"""S0 -> S7 orchestration.

Plain Python by design. A framework goes in only when the state genuinely needs
one; right now the pipeline is a straight line with two early exits (gate
failure, adversarial flag).
"""

from __future__ import annotations

from agent.schemas import GradingResult, Submission


def grade(submission: Submission, *, model: str, n_samples: int = 3) -> GradingResult:
    """Run one submission through the full pipeline."""
    raise NotImplementedError
