"""The five systems every claim is measured against.

Non-negotiable, and in this order of embarrassment: if the full agent does not
beat `TestOnlyBaseline` on C2 and C3, that is a finding to report, not a bug to
bury. The zero-shot baseline exists specifically to isolate whether the
engineering -- sandbox, static analysis, evidence isolation, N-sampling -- adds
anything over a single well-written prompt.

Usage:
    python -m eval.baselines --baseline test_only
"""

from __future__ import annotations

from agent.schemas import GradingResult, Submission


class TestOnlyBaseline:
    """Score purely from the fraction of tests passed. Often strong."""

    name = "test_only"

    def grade(self, submission: Submission) -> GradingResult:
        raise NotImplementedError


class ZeroShotLLMBaseline:
    """Code + rubric in one prompt. No tools, no pipeline, no sampling."""

    name = "zero_shot_llm"

    def grade(self, submission: Submission) -> GradingResult:
        raise NotImplementedError


class StaticOnlyBaseline:
    """ruff + radon thresholds only."""

    name = "static_only"

    def grade(self, submission: Submission) -> GradingResult:
        raise NotImplementedError


class HumanBaseline:
    """Replays recorded human grades (Menagerie) as if they were a system.

    Lets human-vs-human alpha be computed on the same items the agent graded,
    rather than cited from the paper.
    """

    name = "human"

    def grade(self, submission: Submission) -> GradingResult:
        raise NotImplementedError


class FullAgent:
    """The S0-S7 pipeline."""

    name = "full_agent"

    def grade(self, submission: Submission) -> GradingResult:
        raise NotImplementedError


BASELINES = {
    b.name: b
    for b in (TestOnlyBaseline, ZeroShotLLMBaseline, StaticOnlyBaseline,
              HumanBaseline, FullAgent)
}
