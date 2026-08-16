"""Telling a per-minute throttle apart from a spent daily quota.

Getting this backwards is expensive in both directions: treating a daily cap as
retryable burns ten minutes backing off against something that will not clear,
and treating a per-minute throttle as fatal aborts a sweep that only needed to
slow down. Both happened before these tests existed, on real Gemini responses.
"""

from __future__ import annotations

from agent.llm import _is_daily_quota, _quota_summary, _retry_after

# The two errors, as the provider actually returns them.
PER_DAY = (
    "Error code: 429 - {'error': {'code': 429, 'message': 'You exceeded your current "
    "quota. * Quota exceeded for metric: generativelanguage.googleapis.com/"
    "generate_content_free_tier_requests, limit: 20, model: gemini-2.5-flash. Please "
    "retry in 42.7s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'quotaId': "
    "'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaValue': '20'}]}}"
)

PER_MINUTE = (
    "Error code: 429 - {'error': {'code': 429, 'message': 'You exceeded your current "
    "quota. * Quota exceeded for metric: generativelanguage.googleapis.com/"
    "generate_content_free_tier_requests, limit: 10, model: gemini-2.5-flash-lite. "
    "Please retry in 6.4s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'quotaId': "
    "'GenerateRequestsPerMinutePerProjectPerModel-FreeTier', 'quotaValue': '10'}]}}"
)


def test_a_daily_cap_is_recognised():
    assert _is_daily_quota(PER_DAY)
    assert "20 requests/day" in _quota_summary(PER_DAY)


def test_a_per_minute_throttle_is_not_a_daily_cap():
    # Both carry the same metric name; only the quotaId distinguishes them.
    assert not _is_daily_quota(PER_MINUTE)


def test_the_providers_own_retry_hint_is_honoured():
    assert _retry_after(PER_MINUTE, fallback=30.0) == 7.4
    assert _retry_after("no hint here", fallback=30.0) == 30.0


def test_an_absurd_retry_hint_is_capped():
    assert _retry_after("please retry in 8000.0s", fallback=5.0) == 90.0
