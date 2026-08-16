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

import time

from agent import static_analysis
from agent.aggregate import aggregate, correctness_score, load_rubric
from agent.sandbox import SandboxLimits, run_tests
from agent.schemas import (
    Diagnosis,
    GradingResult,
    Misconception,
    Route,
    Span,
    StaticFeatures,
    Submission,
)
from data.problems.loader import load_all


def _whole_file(source: str) -> Span:
    """Evidence span for a system that cannot localise anything better."""
    return Span(start_line=1, end_line=max(1, len(source.splitlines())))


class TestOnlyBaseline:
    """Score purely from the fraction of tests passed. Often strong.

    Its diagnosis is the honest limit of what tests alone can say: everything
    passes, so `OK`; something failed, so *a* bug, named by the majority class.
    That prior is taken from the evaluation set's own label distribution, which
    is the conventional majority-class baseline and is stated as such rather
    than presented as a diagnosis.

    Style, documentation and design are given full marks because tests carry no
    signal about them -- the resulting band error is exactly the cost of
    grading on tests alone, which is what this baseline is here to measure.
    """

    name = "test_only"

    def __init__(self, fallback_label: Misconception = Misconception.CMP):
        self.fallback_label = fallback_label
        self._problems = {p.id: p for p in load_all()}
        self._rubric = load_rubric()

    def grade(self, submission: Submission) -> GradingResult:
        problem = self._problems[submission.problem_id]
        started = time.monotonic()
        results = run_tests(submission.source, problem.tests_path, SandboxLimits())
        elapsed = time.monotonic() - started

        passed_fraction = correctness_score(results, self._rubric)
        all_passed = all(r.passed for r in results) and bool(results)

        score = aggregate(
            results,
            StaticFeatures(docstring_coverage=1.0, comment_ratio=0.05),
            design=1.0,
            rubric=self._rubric,
        )
        return GradingResult(
            submission_id=submission.submission_id,
            score=score,
            diagnosis=Diagnosis(
                label=Misconception.OK if all_passed else self.fallback_label,
                evidence=[_whole_file(submission.source)],
                rationale=(
                    "all tests passed"
                    if all_passed
                    else f"{sum(1 for r in results if not r.passed)} of {len(results)} tests failed"
                ),
                # Confident at the extremes, unsure in between -- the only
                # calibration signal a test count can honestly provide.
                confidence=abs(2 * passed_fraction - 1),
            ),
            route=Route.AUTO,
            model=None,
            latency_s=round(elapsed, 4),
            cost_inr=0.0,
            tokens=0,
        )


class StaticOnlyBaseline:
    """ruff + radon thresholds only; never runs the code.

    Correctness is unobservable to it, so it assumes the code works -- which is
    precisely the failure mode of grading on appearance. Reported to show what
    that assumption costs.
    """

    name = "static_only"

    def __init__(self):
        self._rubric = load_rubric()

    def grade(self, submission: Submission) -> GradingResult:
        started = time.monotonic()
        features = static_analysis.extract(submission.source)
        elapsed = time.monotonic() - started

        from agent.schemas import TestResult

        assumed_pass = [TestResult(test_id="assumed", passed=True, kind="normal")]
        score = aggregate(assumed_pass, features, design=1.0, rubric=self._rubric)
        return GradingResult(
            submission_id=submission.submission_id,
            score=score,
            diagnosis=Diagnosis(
                label=Misconception.OK,
                evidence=[_whole_file(submission.source)],
                rationale="static analysis only; correctness not observed",
                confidence=0.2,
            ),
            route=Route.AUTO,
            latency_s=round(elapsed, 4),
            cost_inr=0.0,
            tokens=0,
        )


class ZeroShotLLMBaseline:
    """Code + rubric in one prompt. No tools, no pipeline, no sampling."""

    name = "zero_shot_llm"

    def grade(self, submission: Submission) -> GradingResult:
        raise NotImplementedError("week 2: needs agent/llm.py and a provider key")


class HumanBaseline:
    """Replays recorded human grades (Menagerie) as if they were a system.

    Lets human-vs-human alpha be computed on the same items the agent graded,
    rather than cited from the paper.
    """

    name = "human"

    def grade(self, submission: Submission) -> GradingResult:
        raise NotImplementedError("week 4: needs the Menagerie loader")


class FullAgent:
    """The S0-S7 pipeline."""

    name = "full_agent"

    def grade(self, submission: Submission) -> GradingResult:
        raise NotImplementedError("week 3: needs S4 diagnosis")


BASELINES = {
    b.name: b
    for b in (TestOnlyBaseline, ZeroShotLLMBaseline, StaticOnlyBaseline, HumanBaseline, FullAgent)
}


def build(name: str, submissions: list[Submission] | None = None):
    """Instantiate a baseline, giving the majority-class prior where needed."""
    if name == TestOnlyBaseline.name and submissions:
        from collections import Counter

        from agent.schemas import CORRECT_LABELS

        bugs = Counter(
            s.true_label for s in submissions if s.true_label and s.true_label not in CORRECT_LABELS
        )
        fallback = bugs.most_common(1)[0][0] if bugs else Misconception.CMP
        return TestOnlyBaseline(fallback_label=fallback)
    return BASELINES[name]()


def main() -> None:
    import argparse

    from eval import harness

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, choices=sorted(BASELINES))
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    harness.run_and_report([args.baseline], limit=args.limit)


if __name__ == "__main__":
    main()
