"""LLM client behaviour that must hold without ever calling a provider."""

from __future__ import annotations

import time

import pytest
from pydantic import BaseModel

from agent.llm import LLMError, ModelConfig, _extract_json, _RateLimiter, complete_structured


class _Answer(BaseModel):
    value: int


class TestJSONExtraction:
    @pytest.mark.parametrize(
        "raw",
        [
            '{"value": 1}',
            '```json\n{"value": 1}\n```',
            'Sure! Here is the result:\n```\n{"value": 1}\n```\nHope that helps.',
            'Thinking... {"value": 1}',
        ],
    )
    def test_json_is_recovered_from_chatty_responses(self, raw):
        # Providers wrap, fence, and preface. None of that reaches a caller:
        # free text is not parsed anywhere outside this module.
        assert _Answer.model_validate_json(_extract_json(raw)).value == 1

    def test_a_response_with_no_object_raises(self):
        with pytest.raises(ValueError):
            _extract_json("I cannot help with that.")


class TestRateLimiter:
    def test_calls_are_spaced_to_the_quota(self):
        limiter = _RateLimiter()
        started = time.monotonic()
        for _ in range(3):
            limiter.wait("m", requests_per_minute=600)  # one per 0.1s
        elapsed = time.monotonic() - started
        # Two gaps after the first (free) call = 0.2s. Compared with a tolerance
        # rather than exactly: sleep can return a hair early, and asserting on
        # the exact boundary makes the test flaky about the thing it measures.
        assert elapsed >= 0.18, elapsed

    def test_zero_disables_pacing(self):
        limiter = _RateLimiter()
        started = time.monotonic()
        for _ in range(50):
            limiter.wait("m", requests_per_minute=0)
        assert time.monotonic() - started < 0.5

    def test_separate_models_have_separate_budgets(self):
        limiter = _RateLimiter()
        started = time.monotonic()
        limiter.wait("a", 60)
        limiter.wait("b", 60)
        assert time.monotonic() - started < 0.5


def test_a_missing_key_fails_loudly_before_any_request(monkeypatch):
    # The failure a developer will actually hit. It must name the variable,
    # not surface as an auth error from three layers down.
    monkeypatch.delenv("NOT_SET_ANYWHERE", raising=False)
    config = ModelConfig(name="m", api_key_env="NOT_SET_ANYWHERE")
    with pytest.raises(LLMError, match="NOT_SET_ANYWHERE"):
        complete_structured("hi", _Answer, config, use_cache=False)
