"""Single provider-agnostic entry point for model calls.

Gemini (AI Studio), Groq, OpenRouter and a local Ollama all speak the
OpenAI-compatible chat API, so one client covers them; the cross-model
cost/accuracy/consistency frontier is a deliverable, which is why no model name
may be hardcoded outside config.

Every call is cached on a hash of (prompt, model, params, run_index). Reruns of
the eval are then free, while consistency runs still draw fresh samples because
run_index is part of the key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ModelConfig:
    name: str  # e.g. "gemini-2.0-flash", "llama-3.3-70b-versatile"
    base_url: str
    api_key_env: str
    temperature: float = 0.0
    max_tokens: int = 2048
    price_per_mtok_in: float = 0.0
    price_per_mtok_out: float = 0.0


def complete_structured(
    prompt: str,
    schema: type[T],
    config: ModelConfig,
    *,
    run_index: int = 0,
    max_retries: int = 3,
) -> T:
    """Call the model and return a validated `schema` instance."""
    raise NotImplementedError
