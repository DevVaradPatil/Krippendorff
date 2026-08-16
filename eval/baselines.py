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

from pydantic import BaseModel, Field

from agent import pipeline, static_analysis
from agent.aggregate import aggregate, band_for, correctness_score, load_rubric
from agent.confidence import RoutingPolicy
from agent.llm import ModelConfig
from agent.sandbox import SandboxLimits, run_tests
from agent.schemas import (
    Diagnosis,
    GradingResult,
    Misconception,
    Route,
    Score,
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
    """Code + rubric in one prompt. No tools, no pipeline, no sampling.

    The control for the whole project: it isolates whether the sandbox, static
    analysis, evidence isolation and N-sampling buy anything over one
    well-written prompt. It therefore gets the submission *raw* -- comments and
    all, no test results, no line numbering, no untrusted-input framing -- and
    is asked for the band directly. That is exactly the naive setup the
    architecture is arguing against, so weakening it deliberately would rig the
    comparison.
    """

    name = "zero_shot_llm"

    def __init__(self, config: ModelConfig, use_cache: bool = True):
        self.config = config
        self.use_cache = use_cache
        self._problems = {p.id: p for p in load_all()}
        self._rubric = load_rubric()
        self._bands = [b["name"] for b in self._rubric["bands"]]

    def grade(self, submission: Submission) -> GradingResult:
        from agent.llm import LLMError, complete_structured

        problem = self._problems[submission.problem_id]
        # Built outside the f-string: nested same-type quotes need PEP 701,
        # which is 3.12-only, and this project supports 3.11.
        bands = ", ".join("{} >= {}".format(b["name"], b["min"]) for b in self._rubric["bands"])
        prompt = (
            f"Grade this intro-Python submission against the rubric.\n\n"
            f"## Problem\n{problem.statement}\n\n"
            f"## Rubric\ncorrectness 60%, style 15%, documentation 10%, design 15%. "
            f"Bands: {bands}\n\n"
            f"## Submission\n```python\n{submission.source}```\n\n"
            f"Give an overall score in [0, 1], the band, and the single "
            f"misconception label from: {', '.join(m.value for m in Misconception)}. "
            f"OK means correct but poorly presented; ALT means correct by a "
            f"different valid approach."
        )
        started = time.monotonic()
        try:
            response, completion = complete_structured(
                prompt,
                _ZeroShotResponse,
                self.config,
                run_index=0,
                use_cache=self.use_cache,
            )
        except LLMError as exc:
            raise RuntimeError(f"zero-shot baseline could not run: {exc}") from exc

        band = (
            response.band
            if response.band in self._bands
            else band_for(response.total_score, self._rubric)
        )
        return GradingResult(
            submission_id=submission.submission_id,
            score=Score(
                correctness=response.total_score,
                style=response.total_score,
                design=response.total_score,
                total=response.total_score,
                band=band,
            ),
            diagnosis=Diagnosis(
                label=response.label,
                evidence=[_whole_file(submission.source)],
                rationale=response.rationale,
                subjective_scores={"design": response.total_score},
                confidence=response.confidence,
            ),
            route=Route.AUTO,
            model=self.config.name,
            tokens=completion.tokens_in + completion.tokens_out,
            cost_inr=round(completion.cost_inr(self.config), 6),
            latency_s=round(time.monotonic() - started, 3),
        )


class _ZeroShotResponse(BaseModel):
    total_score: float = Field(ge=0.0, le=1.0)
    band: str
    label: Misconception
    rationale: str = Field(max_length=600)
    confidence: float = Field(ge=0.0, le=1.0)


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

    def __init__(
        self,
        config: ModelConfig,
        policy: RoutingPolicy | None = None,
        *,
        include_comments: bool = False,
        use_cache: bool = True,
    ):
        self.config = config
        self.policy = policy or RoutingPolicy()
        self.include_comments = include_comments
        self.use_cache = use_cache
        self.run_offset = 0  # set by the harness on each repeat; see run()
        self._problems = {p.id: p for p in load_all()}

    def grade(self, submission: Submission) -> GradingResult:
        return pipeline.grade(
            submission,
            self._problems[submission.problem_id],
            self.config,
            policy=self.policy,
            include_comments=self.include_comments,
            use_cache=self.use_cache,
            run_offset=self.run_offset,
        )


BASELINES = {
    b.name: b
    for b in (TestOnlyBaseline, ZeroShotLLMBaseline, StaticOnlyBaseline, HumanBaseline, FullAgent)
}


#: Systems that cost money to run, and therefore need a configured model.
LLM_SYSTEMS = frozenset({ZeroShotLLMBaseline.name, FullAgent.name})


def build(
    name: str,
    submissions: list[Submission] | None = None,
    *,
    model: ModelConfig | None = None,
    policy: RoutingPolicy | None = None,
    include_comments: bool = False,
):
    """Instantiate a baseline, giving the majority-class prior where needed."""
    if name == TestOnlyBaseline.name and submissions:
        from collections import Counter

        from agent.schemas import CORRECT_LABELS

        bugs = Counter(
            s.true_label for s in submissions if s.true_label and s.true_label not in CORRECT_LABELS
        )
        fallback = bugs.most_common(1)[0][0] if bugs else Misconception.CMP
        return TestOnlyBaseline(fallback_label=fallback)

    if name in LLM_SYSTEMS:
        if model is None:
            raise NotImplementedError(f"{name} needs a model config; none was given")
        if name == ZeroShotLLMBaseline.name:
            return ZeroShotLLMBaseline(model)
        return FullAgent(model, policy, include_comments=include_comments)

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
