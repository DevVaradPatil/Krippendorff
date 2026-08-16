"""S6 - confidence and routing.

Runs S4 N times, measures disagreement, and decides auto-grade vs human review.
This one stage produces two of the project's claims: the disagreement figure is
the C1 consistency instrument, and the routing threshold is the C3 calibration
knob that the risk-coverage curve sweeps.

Route to a human when the samples disagree about the label, when self-reported
confidence is low, when the total sits on a band boundary (where a rounding-
sized difference changes the grade a student sees), or when S4 failed outright.
Deferring is not a failure state -- an agent that grades everything is a
liability, and one that grades 70% and flags the rest is a tool.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from statistics import median

from agent.aggregate import load_rubric
from agent.schemas import Diagnosis, Route, Score


@dataclass(frozen=True)
class RoutingPolicy:
    n_samples: int = 3
    min_agreement: float = 2 / 3  # fraction of samples sharing the modal label
    min_confidence: float = 0.6
    band_margin: float = 0.02  # route if this close to a band edge
    route_adversarial: bool = True


def agreement(samples: list[Diagnosis]) -> float:
    """Fraction of samples agreeing with the modal label."""
    if not samples:
        return 0.0
    counts = Counter(s.label for s in samples)
    return counts.most_common(1)[0][1] / len(samples)


def consensus(samples: list[Diagnosis]) -> Diagnosis:
    """The modal label, carrying the highest-confidence sample's evidence.

    Median rather than mean for the design sub-score and confidence: one
    outlying sample should not drag the grade, and the median of three is the
    sample the other two bracket.
    """
    if not samples:
        raise ValueError("no samples to reach consensus over")
    modal = Counter(s.label for s in samples).most_common(1)[0][0]
    agreeing = [s for s in samples if s.label == modal]
    best = max(agreeing, key=lambda s: s.confidence)
    return Diagnosis(
        label=modal,
        evidence=best.evidence,
        rationale=best.rationale,
        subjective_scores={
            "design": median(s.subjective_scores.get("design", 1.0) for s in agreeing)
        },
        confidence=median(s.confidence for s in samples),
    )


def near_band_edge(total: float, margin: float) -> bool:
    for band in load_rubric()["bands"]:
        edge = band["min"]
        if edge > 0.0 and abs(total - edge) < margin:
            return True
    return False


def route(
    samples: list[Diagnosis],
    score: Score,
    flags: list[str] | None = None,
    policy: RoutingPolicy | None = None,
) -> tuple[Route, str]:
    """Return (route, human-readable reason)."""
    policy = policy or RoutingPolicy()
    flags = flags or []

    if not samples:
        return Route.HUMAN_REVIEW, "diagnosis failed"
    if policy.route_adversarial and flags:
        return Route.HUMAN_REVIEW, f"flagged: {', '.join(flags)}"

    consensus_rate = agreement(samples)
    if consensus_rate < policy.min_agreement:
        labels = ", ".join(sorted({s.label.value for s in samples}))
        return Route.HUMAN_REVIEW, f"samples disagreed ({labels})"

    confidence = median(s.confidence for s in samples)
    if confidence < policy.min_confidence:
        return Route.HUMAN_REVIEW, f"low confidence ({confidence:.2f})"

    if near_band_edge(score.total, policy.band_margin):
        return Route.HUMAN_REVIEW, f"score {score.total:.3f} sits on a band edge"

    return Route.AUTO, f"{consensus_rate:.0%} agreement, confidence {confidence:.2f}"
