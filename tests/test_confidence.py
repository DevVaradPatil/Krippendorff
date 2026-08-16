"""S6 routing, and the cache-key property the consistency claim depends on."""

from __future__ import annotations

from agent.confidence import RoutingPolicy, agreement, consensus, route
from agent.llm import ModelConfig, cache_key
from agent.schemas import Diagnosis, Misconception, Route, Score, Span


def _diagnosis(label: Misconception, confidence: float, design: float = 1.0) -> Diagnosis:
    return Diagnosis(
        label=label,
        evidence=[Span(start_line=1, end_line=1)],
        rationale="because",
        subjective_scores={"design": design},
        confidence=confidence,
    )


def _score(total: float) -> Score:
    return Score(correctness=total, style=1.0, design=1.0, total=total, band="A")


class TestConsensus:
    def test_modal_label_wins(self):
        samples = [
            _diagnosis(Misconception.OBO, 0.9),
            _diagnosis(Misconception.OBO, 0.7),
            _diagnosis(Misconception.CMP, 0.8),
        ]
        assert agreement(samples) == 2 / 3
        assert consensus(samples).label is Misconception.OBO

    def test_design_is_the_median_not_the_mean(self):
        # One wild sample should not drag the only sub-score the model owns.
        samples = [
            _diagnosis(Misconception.OBO, 0.9, design=1.0),
            _diagnosis(Misconception.OBO, 0.9, design=0.9),
            _diagnosis(Misconception.OBO, 0.9, design=0.0),
        ]
        assert consensus(samples).subjective_scores["design"] == 0.9


class TestRouting:
    def test_unanimous_and_confident_is_auto_graded(self):
        samples = [_diagnosis(Misconception.OBO, 0.9)] * 3
        destination, _ = route(samples, _score(0.5), policy=RoutingPolicy())
        assert destination is Route.AUTO

    def test_disagreement_defers(self):
        samples = [
            _diagnosis(Misconception.OBO, 0.9),
            _diagnosis(Misconception.CMP, 0.9),
            _diagnosis(Misconception.DIV, 0.9),
        ]
        destination, reason = route(samples, _score(0.5))
        assert destination is Route.HUMAN_REVIEW
        assert "disagreed" in reason

    def test_low_confidence_defers(self):
        samples = [_diagnosis(Misconception.OBO, 0.2)] * 3
        destination, reason = route(samples, _score(0.5))
        assert destination is Route.HUMAN_REVIEW
        assert "confidence" in reason

    def test_a_score_on_a_band_edge_defers(self):
        # 0.850 is the A/B boundary: a rounding-sized difference changes the
        # grade a student sees, so a human decides it.
        samples = [_diagnosis(Misconception.OK, 0.95)] * 3
        destination, reason = route(samples, _score(0.8505))
        assert destination is Route.HUMAN_REVIEW
        assert "band edge" in reason

    def test_a_failed_diagnosis_defers_rather_than_guessing(self):
        destination, reason = route([], _score(0.5))
        assert destination is Route.HUMAN_REVIEW
        assert reason == "diagnosis failed"


class TestCacheKey:
    config = ModelConfig(name="m")

    def test_run_index_changes_the_key(self):
        # If it did not, the N=5 consistency runs would replay one cached answer
        # and report perfect self-agreement without ever asking the model twice.
        from agent.diagnose import _DiagnosisResponse

        first = cache_key("p", self.config, _DiagnosisResponse, run_index=0)
        second = cache_key("p", self.config, _DiagnosisResponse, run_index=1)
        assert first != second

    def test_same_inputs_give_the_same_key(self):
        from agent.diagnose import _DiagnosisResponse

        assert cache_key("p", self.config, _DiagnosisResponse, 0) == cache_key(
            "p", self.config, _DiagnosisResponse, 0
        )
