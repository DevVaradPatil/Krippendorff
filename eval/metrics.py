"""Metrics for C1-C4 plus operational cost.

Reference points from the literature that every result is reported against
(Messer et al. 2025): human inter-rater Krippendorff's alpha ~0.22 on
correctness, <0.1 on style/readability/documentation, and 1.79 grade bands of
mean *self*-disagreement. A raw agent-vs-human agreement number without one of
these beside it is meaningless and must not appear in the report.
"""

from __future__ import annotations

from collections import Counter
from statistics import mean

from agent.aggregate import band_distance, band_for, load_rubric
from agent.schemas import CORRECT_LABELS, GradingResult, Misconception, Submission

HUMAN_SELF_DISAGREEMENT_BANDS = 1.79
HUMAN_INTERRATER_ALPHA_CORRECTNESS = 0.22


def truth_band(submission: Submission) -> str:
    return band_for(submission.true_score or 0.0, load_rubric())


# --- C1: consistency -------------------------------------------------------


def self_agreement(runs: list[list[GradingResult]]) -> dict[str, float]:
    """Exact-match rate and mean absolute band distance across N reruns.

    `runs` is one list per repeat, aligned by position. A deterministic system
    scores 1.0 / 0.0 here by construction, which is the point: it isolates how
    much of the agent's variance comes from the LLM rather than the pipeline.
    """
    # Keys are prefixed `self_`: this is disagreement of a system with itself,
    # not with ground truth, and merging the two into one `mean_band_distance`
    # silently overwrote the accuracy figure in the summary table.
    if len(runs) < 2:
        return {"exact_match_rate": 1.0, "self_mean_band_distance": 0.0, "n_runs": 1}

    exact, distances = [], []
    for results in zip(*runs, strict=True):
        bands = [r.score.band for r in results]
        exact.append(1.0 if len(set(bands)) == 1 else 0.0)
        pairs = [
            band_distance(bands[i], bands[j])
            for i in range(len(bands))
            for j in range(i + 1, len(bands))
        ]
        distances.append(mean(pairs) if pairs else 0.0)

    return {
        "exact_match_rate": mean(exact),
        "self_mean_band_distance": mean(distances),
        "n_runs": len(runs),
    }


def krippendorff_alpha(ratings: list[list[float | None]]) -> float:
    """Alpha over a raters x items matrix; used for both agent and humans."""
    try:
        import krippendorff
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("pip install krippendorff to compute alpha") from exc
    return float(krippendorff.alpha(reliability_data=ratings, level_of_measurement="ordinal"))


# --- C2: diagnosis ---------------------------------------------------------


def _labels(results: list[GradingResult]) -> list[Misconception | None]:
    return [r.diagnosis.label if r.diagnosis else None for r in results]


def macro_f1(true: list[Misconception], pred: list[Misconception | None]) -> float:
    """Unweighted mean F1 over the labels that actually appear in `true`.

    Macro rather than micro: a 14-class taxonomy where CMP is a quarter of the
    set would let a model that only ever predicts CMP look respectable.
    """
    paired = list(zip(true, pred, strict=True))
    scores = []
    for cls in sorted({t.value for t in true}):
        predicted_cls = [(t, p) for t, p in paired if p and p.value == cls]
        actual_cls = [(t, p) for t, p in paired if t.value == cls]
        tp = sum(1 for t, _ in predicted_cls if t.value == cls)
        precision = tp / len(predicted_cls) if predicted_cls else 0.0
        recall = tp / len(actual_cls) if actual_cls else 0.0
        denominator = precision + recall
        scores.append(2 * precision * recall / denominator if denominator else 0.0)
    return mean(scores) if scores else 0.0


def per_class_f1(
    true: list[Misconception], pred: list[Misconception | None]
) -> dict[str, dict[str, float]]:
    """Precision, recall, F1 and support for each label present in `true`.

    The aggregate macro-F1 hides which classes carry it. With a taxonomy this
    skewed -- CMP is a quarter of the set, TYPE is one item -- the per-class
    table is what says whether a score reflects broad competence or one easy
    class, and it is the honest thing to publish beside the headline.
    """
    paired = list(zip(true, pred, strict=True))
    out: dict[str, dict[str, float]] = {}
    for cls in sorted({t.value for t in true}):
        predicted_cls = [t for t, p in paired if p and p.value == cls]
        actual_cls = [t for t, _ in paired if t.value == cls]
        tp = sum(1 for t in predicted_cls if t.value == cls)
        precision = tp / len(predicted_cls) if predicted_cls else 0.0
        recall = tp / len(actual_cls) if actual_cls else 0.0
        denominator = precision + recall
        out[cls] = {
            "precision": precision,
            "recall": recall,
            "f1": 2 * precision * recall / denominator if denominator else 0.0,
            "support": len(actual_cls),
        }
    return out


def confusion_matrix(
    true: list[Misconception], pred: list[Misconception | None]
) -> dict[str, Counter]:
    matrix: dict[str, Counter] = {}
    for t, p in zip(true, pred, strict=True):
        matrix.setdefault(t.value, Counter())[p.value if p else "NONE"] += 1
    return matrix


def false_positive_rate_on_correct(
    true: list[Misconception], pred: list[Misconception | None]
) -> float:
    """Rate at which OK/ALT submissions are flagged as buggy.

    The single most important number in C2: penalising correct-but-unusual work
    is the failure mode that actually harms students.
    """
    correct = [(t, p) for t, p in zip(true, pred, strict=True) if t in CORRECT_LABELS]
    if not correct:
        return 0.0
    flagged = sum(1 for _, p in correct if p is None or p not in CORRECT_LABELS)
    return flagged / len(correct)


# --- band-level accuracy ---------------------------------------------------


def band_accuracy(results: list[GradingResult], submissions: list[Submission]) -> dict[str, float]:
    exact = [
        1.0 if r.score.band == truth_band(s) else 0.0
        for r, s in zip(results, submissions, strict=True)
    ]
    distances = [
        float(band_distance(r.score.band, truth_band(s)))
        for r, s in zip(results, submissions, strict=True)
    ]
    within_one = [1.0 if d <= 1 else 0.0 for d in distances]
    # Bands are coarse: a system can be wrong about style and documentation and
    # still land in the right band because correctness dominates the weighting.
    # The raw score error is what shows that difference.
    score_error = [
        abs(r.score.total - (s.true_score or 0.0))
        for r, s in zip(results, submissions, strict=True)
    ]
    return {
        "band_accuracy": mean(exact) if exact else 0.0,
        "within_one_band": mean(within_one) if within_one else 0.0,
        "mean_band_distance": mean(distances) if distances else 0.0,
        "mean_score_error": mean(score_error) if score_error else 0.0,
    }


# --- C3: calibration -------------------------------------------------------


def risk_coverage_curve(
    results: list[GradingResult], submissions: list[Submission]
) -> list[tuple[float, float]]:
    """(coverage, accuracy) as the confidence threshold sweeps.

    Sort by confidence, then read off accuracy over the most-confident prefix.
    A useful system's curve rises to the left: the cases it keeps are the ones
    it gets right.
    """
    paired = sorted(
        zip(results, submissions, strict=True),
        key=lambda pair: pair[0].diagnosis.confidence if pair[0].diagnosis else 0.0,
        reverse=True,
    )
    curve = []
    correct = 0
    for index, (result, submission) in enumerate(paired, start=1):
        correct += 1 if result.score.band == truth_band(submission) else 0
        curve.append((index / len(paired), correct / index))
    return curve


def accuracy_at_coverage(
    results: list[GradingResult], submissions: list[Submission], coverage: float = 0.7
) -> float:
    curve = risk_coverage_curve(results, submissions)
    for point_coverage, accuracy in curve:
        if point_coverage >= coverage:
            return accuracy
    return curve[-1][1] if curve else 0.0


def expected_calibration_error(
    results: list[GradingResult], submissions: list[Submission], bins: int = 10
) -> float:
    buckets: dict[int, list[tuple[float, float]]] = {}
    for result, submission in zip(results, submissions, strict=True):
        confidence = result.diagnosis.confidence if result.diagnosis else 0.0
        index = min(bins - 1, int(confidence * bins))
        hit = 1.0 if result.score.band == truth_band(submission) else 0.0
        buckets.setdefault(index, []).append((confidence, hit))

    total = sum(len(v) for v in buckets.values())
    if not total:
        return 0.0
    return sum(
        len(items) / total * abs(mean(c for c, _ in items) - mean(h for _, h in items))
        for items in buckets.values()
    )


# --- operational -----------------------------------------------------------


def operational_summary(results: list[GradingResult]) -> dict[str, float]:
    """Cost per submission (INR + tokens), p50/p95 latency, deferral rate."""
    latencies = sorted(r.latency_s or 0.0 for r in results)
    if not latencies:
        return {}

    def percentile(p: float) -> float:
        return latencies[min(len(latencies) - 1, int(p * len(latencies)))]

    deferred = sum(1 for r in results if r.route.value == "human_review")
    return {
        "p50_latency_s": percentile(0.50),
        "p95_latency_s": percentile(0.95),
        "mean_tokens": mean(r.tokens or 0 for r in results),
        "mean_cost_inr": mean(r.cost_inr or 0.0 for r in results),
        "deferral_rate": deferred / len(results),
    }
