"""Metrics for C1-C4 plus operational cost.

Reference points from the literature that every result is reported against
(Messer et al. 2025): human inter-rater Krippendorff's alpha ~0.22 on
correctness, <0.1 on style/readability/documentation, and 1.79 grade bands of
mean *self*-disagreement. A raw agent-vs-human agreement number without one of
these beside it is meaningless and must not appear in the report.
"""

from __future__ import annotations

from agent.schemas import GradingResult, Misconception

HUMAN_SELF_DISAGREEMENT_BANDS = 1.79
HUMAN_INTERRATER_ALPHA_CORRECTNESS = 0.22


# --- C1: consistency -------------------------------------------------------

def self_agreement(runs: list[list[GradingResult]]) -> dict[str, float]:
    """Exact-match rate and mean absolute band distance across N reruns."""
    raise NotImplementedError


def krippendorff_alpha(ratings: list[list[float | None]]) -> float:
    """Alpha over a raters x items matrix; used for both agent and humans."""
    raise NotImplementedError


# --- C2: diagnosis ---------------------------------------------------------

def macro_f1(true: list[Misconception], pred: list[Misconception]) -> float:
    raise NotImplementedError


def confusion_matrix(true: list[Misconception], pred: list[Misconception]):
    raise NotImplementedError


def false_positive_rate_on_correct(
    true: list[Misconception], pred: list[Misconception]
) -> float:
    """Rate at which OK/ALT submissions are flagged as buggy.

    The single most important number in C2: penalising correct-but-unusual work
    is the failure mode that actually harms students.
    """
    raise NotImplementedError


# --- C3: calibration -------------------------------------------------------

def risk_coverage_curve(results: list[GradingResult]) -> list[tuple[float, float]]:
    """(coverage, accuracy) points as the routing threshold sweeps."""
    raise NotImplementedError


def expected_calibration_error(results: list[GradingResult], bins: int = 10) -> float:
    raise NotImplementedError


# --- operational -----------------------------------------------------------

def operational_summary(results: list[GradingResult]) -> dict[str, float]:
    """Cost per submission (INR + tokens), p50/p95 latency, throughput."""
    raise NotImplementedError
