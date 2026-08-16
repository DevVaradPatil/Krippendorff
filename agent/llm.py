"""Single provider-agnostic entry point for model calls.

Gemini (AI Studio), Groq, OpenRouter, OpenAI and a local Ollama all speak the
OpenAI-compatible chat API, so one client covers them; the cross-model
cost/accuracy/consistency frontier is a deliverable, which is why no model name
may be hardcoded outside config.

Every call is cached on a hash of (prompt, model, params, run_index). Reruns of
the eval are free, while the N-sample consistency runs still reach the API
because `run_index` is part of the key -- which is the point: those runs exist to
measure how much the model disagrees with itself, and replaying one cached
answer would report perfect consistency for free.

Structured output is enforced here, not parsed downstream. The model is asked
for JSON, the response is validated against a Pydantic schema, and a failure is
retried with the validation error fed back. Free text never escapes this module.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "llm"
T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ModelConfig:
    name: str  # e.g. "gemini-2.0-flash", "llama-3.3-70b-versatile"
    base_url: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    temperature: float = 0.0
    max_tokens: int = 2048
    price_per_mtok_in: float = 0.0  # USD per million input tokens
    price_per_mtok_out: float = 0.0
    inr_per_usd: float = 87.0
    #: Providers differ in how much of the structured-output spec they support.
    json_mode: str = "json_object"  # json_object | json_schema | prompt_only
    #: Free tiers are rate-limited per minute; 0 disables client-side pacing.
    #: Set it below the published limit -- discovering the ceiling by getting
    #: 429s halfway through a 480-call sweep wastes the whole run.
    requests_per_minute: int = 0
    #: Reasoning models spend output tokens thinking before they answer. S4 is a
    #: single-label choice over evidence that is already assembled, so "none"
    #: keeps the budget for the answer. Providers that ignore it are unaffected.
    reasoning_effort: str | None = None


class _RateLimiter:
    """Spaces calls out across threads to stay under a per-minute quota."""

    def __init__(self):
        self._next_allowed: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, key: str, requests_per_minute: int) -> None:
        if requests_per_minute <= 0:
            return
        interval = 60.0 / requests_per_minute
        with self._lock:
            now = time.monotonic()
            earliest = max(now, self._next_allowed.get(key, 0.0))
            self._next_allowed[key] = earliest + interval
            delay = earliest - now
        if delay > 0:
            time.sleep(delay)


LIMITER = _RateLimiter()


@dataclass
class Completion:
    parsed: BaseModel
    tokens_in: int = 0
    tokens_out: int = 0
    latency_s: float = 0.0
    cached: bool = False
    attempts: int = 1
    raw: str = ""

    def cost_inr(self, config: ModelConfig) -> float:
        usd = (
            self.tokens_in / 1e6 * config.price_per_mtok_in
            + self.tokens_out / 1e6 * config.price_per_mtok_out
        )
        return usd * config.inr_per_usd


class LLMError(RuntimeError):
    """Raised when a model cannot produce a valid structured answer."""


class QuotaExhaustedError(RuntimeError):
    """The provider's *daily* quota is gone.

    Deliberately not an ``LLMError``: a per-minute 429 is worth waiting out, but
    a daily cap is not, and it must not be swallowed into a per-submission
    "diagnosis failed" either. That would quietly turn an infrastructure outage
    into a page of human-review deferrals that look like agent behaviour. It
    propagates, the run stops, and the cache keeps everything already paid for.
    """


@dataclass
class _Usage:
    calls: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cache_hits: int = 0
    parse_retries: int = 0
    rate_limited: int = 0
    by_model: dict[str, int] = field(default_factory=dict)


USAGE = _Usage()


def _client(config: ModelConfig):
    from openai import OpenAI

    key = os.environ.get(config.api_key_env)
    if not key:
        raise LLMError(
            f"{config.api_key_env} is not set. Add it to .env or the environment; "
            "no model call can be made without it."
        )
    return OpenAI(api_key=key, base_url=config.base_url, timeout=120.0, max_retries=2)


def cache_key(prompt: str, config: ModelConfig, schema: type[T], run_index: int) -> str:
    payload = json.dumps(
        {
            "prompt": prompt,
            "model": config.name,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "schema": schema.model_json_schema(),
            "run_index": run_index,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def complete_structured(
    prompt: str,
    schema: type[T],
    config: ModelConfig,
    *,
    system: str | None = None,
    run_index: int = 0,
    max_retries: int = 3,
    use_cache: bool = True,
) -> tuple[T, Completion]:
    """Call the model and return a validated `schema` instance."""
    key = cache_key(prompt, config, schema, run_index)
    cached_path = CACHE_DIR / f"{key}.json"
    if use_cache and cached_path.exists():
        record = json.loads(cached_path.read_text(encoding="utf-8"))
        USAGE.cache_hits += 1
        parsed = schema.model_validate(record["parsed"])
        return parsed, Completion(
            parsed=parsed,
            tokens_in=record.get("tokens_in", 0),
            tokens_out=record.get("tokens_out", 0),
            latency_s=record.get("latency_s", 0.0),
            cached=True,
            raw=record.get("raw", ""),
        )

    client = _client(config)
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": _with_schema(prompt, schema)})

    started = time.monotonic()
    last_error: str | None = None
    tokens_in = tokens_out = 0

    for attempt in range(1, max_retries + 1):
        LIMITER.wait(config.name, config.requests_per_minute)
        response = _call_with_backoff(client, config, messages, schema)
        usage = getattr(response, "usage", None)
        tokens_in += getattr(usage, "prompt_tokens", 0) or 0
        tokens_out += getattr(usage, "completion_tokens", 0) or 0
        raw = response.choices[0].message.content or ""

        try:
            parsed = schema.model_validate_json(_extract_json(raw))
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)[:800]
            USAGE.parse_retries += 1
            # Feed the failure back rather than guessing: the model usually
            # fixes its own schema violation when shown the validator's words.
            messages.append({"role": "assistant", "content": raw[:2000]})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "That response failed schema validation:\n"
                        f"{last_error}\n\nReturn only corrected JSON."
                    ),
                }
            )
            continue

        completion = Completion(
            parsed=parsed,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_s=time.monotonic() - started,
            attempts=attempt,
            raw=raw,
        )
        USAGE.calls += 1
        USAGE.tokens_in += tokens_in
        USAGE.tokens_out += tokens_out
        USAGE.by_model[config.name] = USAGE.by_model.get(config.name, 0) + 1

        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cached_path.write_text(
                json.dumps(
                    {
                        "parsed": parsed.model_dump(mode="json"),
                        "tokens_in": tokens_in,
                        "tokens_out": tokens_out,
                        "latency_s": completion.latency_s,
                        "raw": raw[:4000],
                    },
                    indent=1,
                ),
                encoding="utf-8",
            )
        return parsed, completion

    raise LLMError(
        f"{config.name} failed to produce valid {schema.__name__} after "
        f"{max_retries} attempts. Last error: {last_error}"
    )


def _call_with_backoff(client, config: ModelConfig, messages, schema, tries: int = 5):
    """Retry on rate limiting. A free tier's 429 is expected, not exceptional."""
    from openai import APIStatusError, RateLimitError

    extra: dict[str, Any] = {}
    if config.reasoning_effort:
        extra["reasoning_effort"] = config.reasoning_effort

    delay = 5.0
    for attempt in range(1, tries + 1):
        try:
            return client.chat.completions.create(
                model=config.name,
                messages=messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                **extra,
                **_response_format(config, schema),
            )
        except (RateLimitError, APIStatusError) as exc:
            status = getattr(exc, "status_code", None)
            text = str(exc)
            if _is_daily_quota(text):
                raise QuotaExhaustedError(
                    f"{config.name}: daily free-tier quota exhausted. "
                    f"{_quota_summary(text)} Cached calls are kept; rerun after "
                    "the quota resets or switch --model."
                ) from exc
            if status not in (429, 500, 502, 503, 529) or attempt == tries:
                raise
            USAGE.rate_limited += 1
            time.sleep(_retry_after(text, delay))
            delay = min(delay * 2, 60.0)
    raise LLMError("unreachable")


# Match the quota *id* ("...PerDayPerProjectPerModel..."), never the metric
# name: `generate_content_free_tier_requests` is reported for per-minute limits
# too, so matching it turns an ordinary throttle into a false "out of quota"
# abort -- which is exactly what happened on the first sweep.
_DAILY = re.compile(r"PerDay", re.IGNORECASE)
_QUOTA_VALUE = re.compile(r"quotaValue['\"]?:\s*['\"]?(\d+)")
_RETRY_AFTER = re.compile(r"retry in ([\d.]+)s")


def _is_daily_quota(text: str) -> bool:
    return bool(_DAILY.search(text))


def _quota_summary(text: str) -> str:
    found = _QUOTA_VALUE.search(text)
    return f"Limit is {found.group(1)} requests/day." if found else ""


def _retry_after(text: str, fallback: float) -> float:
    """Honour the provider's own retry hint when it gives one."""
    found = _RETRY_AFTER.search(text)
    return min(float(found.group(1)) + 1.0, 90.0) if found else fallback


def _response_format(config: ModelConfig, schema: type[T]) -> dict[str, Any]:
    if config.json_mode == "json_schema":
        return {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                    "strict": False,
                },
            }
        }
    if config.json_mode == "json_object":
        return {"response_format": {"type": "json_object"}}
    return {}


def _with_schema(prompt: str, schema: type[T]) -> str:
    return (
        f"{prompt}\n\nRespond with JSON only, matching this schema exactly:\n"
        f"{json.dumps(schema.model_json_schema(), indent=1)}"
    )


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _extract_json(raw: str) -> str:
    """Pull the JSON object out of a response that may be fenced or chatty."""
    text = raw.strip()
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"no JSON object in response: {raw[:200]!r}")
    return text[start : end + 1]


def load_model_config(config: dict[str, Any], which: str = "primary") -> ModelConfig:
    """Build a ModelConfig from the `models:` block of an eval config."""
    entry = dict(config["models"][which])
    return ModelConfig(**entry)
