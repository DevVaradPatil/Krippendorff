"""S6 - confidence and routing.

Runs S4 N times, measures disagreement, and decides auto-grade vs human review.
This one stage produces two of the project's claims: the disagreement figure is
the C1 consistency instrument, and the routing threshold is the C3 calibration
knob that the risk-coverage curve sweeps.

Route to a human when: label variance across samples is high, self-reported
confidence is low, the score sits on a band boundary, or the adversarial
pre-filter flagged the submission.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent.schemas import Diagnosis, Route, Score


@dataclass(frozen=True)
class RoutingPolicy:
    n_samples: int = 3
    min_agreement: float = 2 / 3  # fraction of samples sharing the modal label
    min_confidence: float = 0.6
    band_margin: float = 0.05  # route if within this distance of a band edge
    route_adversarial: bool = True


def agreement(samples: list[Diagnosis]) -> float:
    """Fraction of samples agreeing with the modal label."""
    raise NotImplementedError


def route(
    samples: list[Diagnosis],
    score: Score,
    flags: list[str],
    policy: RoutingPolicy | None = None,
) -> tuple[Route, str]:
    """Return (route, human-readable reason)."""
    raise NotImplementedError
