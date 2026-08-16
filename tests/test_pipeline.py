"""End-to-end pipeline wiring, with the model stubbed out.

The point is to prove the plumbing before a provider key exists: that S1 feeds
correctness, S2 feeds style, S4 feeds *only* design, S6 routes on disagreement,
and a hallucinated span becomes a deferral rather than a grade. None of that is
about model quality, and none of it should need a paid call to check.
"""

from __future__ import annotations

import pytest

from agent import diagnose as s4
from agent import pipeline
from agent.confidence import RoutingPolicy
from agent.llm import Completion, ModelConfig
from agent.sandbox import available
from agent.schemas import Misconception, Route
from data.problems.loader import load_all
from eval.harness import load_submissions

CONFIG = ModelConfig(name="stub", api_key_env="UNUSED")


@pytest.fixture(scope="module")
def case():
    if not available():
        pytest.skip("Docker daemon unreachable")
    submissions = load_submissions()
    problems = {p.id: p for p in load_all()}
    submission = next(s for s in submissions if s.true_label is Misconception.OBO)
    return submission, problems[submission.problem_id]


def _stub(monkeypatch, labels, design=1.0, confidence=0.9, span=(1, 2)):
    """Make S4 return a scripted sequence, one entry per sample."""
    calls = iter(labels)

    def fake(prompt, schema, config, **kwargs):
        response = schema(
            label=next(calls),
            start_line=span[0],
            end_line=span[1],
            rationale="stubbed",
            design_score=design,
            confidence=confidence,
        )
        return response, Completion(parsed=response, tokens_in=10, tokens_out=5)

    monkeypatch.setattr(s4, "complete_structured", fake)


def test_agreement_auto_grades_and_scores_from_the_right_stages(monkeypatch, case):
    submission, problem = case
    _stub(monkeypatch, [Misconception.OBO] * 3, design=1.0)
    result = pipeline.grade(submission, problem, CONFIG, use_cache=False)

    assert result.route is Route.AUTO
    assert result.diagnosis.label is Misconception.OBO
    assert result.consistency_samples == ["OBO"] * 3
    # Correctness came from the sandbox, not the model: this submission is a
    # real mutant, so it must have lost marks there.
    assert 0.0 <= result.score.correctness < 1.0


def test_the_model_moves_design_and_nothing_else(monkeypatch, case):
    submission, problem = case
    _stub(monkeypatch, [Misconception.OBO] * 3, design=1.0)
    generous = pipeline.grade(submission, problem, CONFIG, use_cache=False)
    _stub(monkeypatch, [Misconception.OBO] * 3, design=0.0)
    harsh = pipeline.grade(submission, problem, CONFIG, use_cache=False)

    assert generous.score.correctness == harsh.score.correctness
    assert generous.score.style == harsh.score.style
    assert harsh.score.design < generous.score.design
    # Design carries 15% of the rubric, so swinging it from 1.0 to 0.0 may move
    # the total by at most that much. Anything more means the model leaked into
    # a criterion it does not own.
    assert generous.score.total - harsh.score.total == pytest.approx(0.15, abs=1e-6)


def test_disagreeing_samples_defer(monkeypatch, case):
    submission, problem = case
    _stub(monkeypatch, [Misconception.OBO, Misconception.CMP, Misconception.DIV])
    result = pipeline.grade(submission, problem, CONFIG, use_cache=False)
    assert result.route is Route.HUMAN_REVIEW
    assert "disagreed" in result.route_reason


def test_a_hallucinated_span_defers_rather_than_grading(monkeypatch, case):
    submission, problem = case
    _stub(monkeypatch, [Misconception.OBO] * 3, span=(9000, 9001))
    result = pipeline.grade(submission, problem, CONFIG, use_cache=False)

    assert result.diagnosis is None
    assert result.route is Route.HUMAN_REVIEW
    # Still scored on correctness and style: the tests ran regardless of what
    # the model said, which is the whole point of the split.
    assert result.score.correctness < 1.0


def test_low_confidence_defers(monkeypatch, case):
    submission, problem = case
    _stub(monkeypatch, [Misconception.OBO] * 3, confidence=0.1)
    result = pipeline.grade(submission, problem, CONFIG, use_cache=False)
    assert result.route is Route.HUMAN_REVIEW
    assert "confidence" in result.route_reason


def test_sample_count_follows_the_policy(monkeypatch, case):
    submission, problem = case
    _stub(monkeypatch, [Misconception.OBO] * 5)
    result = pipeline.grade(
        submission, problem, CONFIG, policy=RoutingPolicy(n_samples=5), use_cache=False
    )
    assert len(result.consistency_samples) == 5
