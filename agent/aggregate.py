"""S5 - score aggregation.

Pure function of (test results, static features, diagnosis, rubric). No model
call. Correctness comes from S1, style from S2, design/documentation from S4,
combined with the weights in ``rubric/rubric.yaml`` and mapped to a band.

The same function computes the ground-truth score for synthetic submissions,
which is what makes those labels rule-derived rather than opinion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent.schemas import Diagnosis, Score, StaticFeatures, TestResult

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubric" / "rubric.yaml"


def load_rubric(path: Path = RUBRIC_PATH) -> dict[str, Any]:
    raise NotImplementedError


def aggregate(
    results: list[TestResult],
    features: StaticFeatures,
    diagnosis: Diagnosis | None,
    rubric: dict[str, Any],
) -> Score:
    raise NotImplementedError
