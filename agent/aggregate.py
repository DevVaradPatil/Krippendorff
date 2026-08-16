"""S5 - score aggregation.

Pure function of (test results, static features, design score, rubric). No model
call, no randomness: the same inputs always produce the same band, which is what
lets the consistency claim isolate LLM variance from pipeline variance.

The same function computes the ground-truth score for synthetic submissions.
That is deliberate -- ground truth is *derived by rule* from what the mutation
did to the tests and to the code, never asked of a model or a grader.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

from agent.schemas import Score, StaticFeatures, TestResult

RUBRIC_PATH = Path(__file__).resolve().parent.parent / "rubric" / "rubric.yaml"


@cache
def load_rubric(path: Path = RUBRIC_PATH) -> dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def correctness_score(results: list[TestResult], rubric: dict[str, Any]) -> float:
    """Weighted fraction of tests passed. The only source of correctness."""
    if not results:
        return 0.0
    weights = rubric["criteria"]["correctness"]["test_kind_weights"]
    earned = sum(weights.get(r.kind, 1.0) for r in results if r.passed)
    total = sum(weights.get(r.kind, 1.0) for r in results)
    return earned / total if total else 0.0


def style_score(features: StaticFeatures, rubric: dict[str, Any]) -> float:
    """Deterministic style score from ruff counts and radon complexity."""
    thresholds = rubric["criteria"]["style"]["thresholds"]
    score = 1.0

    violations = sum(features.ruff_violations.values())
    per_100 = violations / max(features.loc, 1) * 100
    allowed = thresholds["ruff_violations_per_100_loc_max"]
    if per_100 > allowed:
        score -= min(0.5, (per_100 - allowed) / 100)

    complexity = features.cyclomatic_complexity or 1.0
    ceiling = thresholds["cyclomatic_complexity_max"]
    if complexity > ceiling:
        score -= min(0.3, (complexity - ceiling) * 0.05)

    return max(0.0, min(1.0, score))


def documentation_score(features: StaticFeatures) -> float:
    """Docstring coverage, with a smaller credit for explanatory comments."""
    comments = min(1.0, features.comment_ratio / 0.05)
    return max(0.0, min(1.0, 0.75 * features.docstring_coverage + 0.25 * comments))


def band_for(total: float, rubric: dict[str, Any]) -> str:
    for band in rubric["bands"]:
        if total >= band["min"]:
            return band["name"]
    return rubric["bands"][-1]["name"]


def aggregate(
    results: list[TestResult],
    features: StaticFeatures,
    design: float,
    rubric: dict[str, Any] | None = None,
) -> Score:
    """Combine the per-criterion scores using the weights in the rubric."""
    rubric = rubric or load_rubric()
    criteria = rubric["criteria"]

    correctness = correctness_score(results, rubric)
    style = style_score(features, rubric)
    documentation = documentation_score(features)
    design = max(0.0, min(1.0, design))

    total = (
        correctness * criteria["correctness"]["weight"]
        + style * criteria["style"]["weight"]
        + documentation * criteria["documentation"]["weight"]
        + design * criteria["design"]["weight"]
    )
    return Score(
        correctness=round(correctness, 6),
        style=round(style, 6),
        design=round(design, 6),
        total=round(total, 6),
        band=band_for(total, rubric),
    )


def band_distance(a: str, b: str, rubric: dict[str, Any] | None = None) -> int:
    """How many bands apart two grades are. The unit for the C1 claim."""
    rubric = rubric or load_rubric()
    order = [band["name"] for band in rubric["bands"]]
    return abs(order.index(a) - order.index(b))
