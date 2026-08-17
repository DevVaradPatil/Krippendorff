"""Regenerate every figure in the report from `results/runs.jsonl`.

Figures are derived, never hand-edited: the JSONL is the record, and any plot
that cannot be rebuilt from it does not belong in the report. Re-running this is
free -- it makes no model calls and reads no sandbox.

Usage:
    python -m eval.figures
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from agent.aggregate import band_for, load_rubric  # noqa: E402
from agent.schemas import CORRECT_LABELS, Misconception  # noqa: E402
from eval import metrics  # noqa: E402
from eval.harness import RESULTS_DIR, load_submissions  # noqa: E402

FIGURES = RESULTS_DIR / "figures"

# Deliberately colour-blind-safe and readable in grayscale: these end up in a
# README that people skim on phones.
INK = "#1b1b1b"
GRID = "#d8d8d8"
SERIES = {
    "full_agent": "#1f4e79",
    "zero_shot_llm": "#c0504d",
    "test_only": "#7f7f7f",
    "static_only": "#bfbfbf",
}
LABELS = {
    "full_agent": "Full agent",
    "zero_shot_llm": "Zero-shot LLM",
    "test_only": "Test-only",
    "static_only": "Static-only",
}


def _style(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, color=INK, fontsize=11, pad=10)
    ax.set_xlabel(xlabel, color=INK, fontsize=9)
    ax.set_ylabel(ylabel, color=INK, fontsize=9)
    ax.tick_params(colors=INK, labelsize=8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.grid(axis="y", color=GRID, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


#: The model whose numbers the report quotes. Figures pin it explicitly rather
#: than taking whatever ran last.
HEADLINE_MODEL = "gemini-3.1-flash-lite"


def load_runs(
    path: Path | None = None, model: str = HEADLINE_MODEL
) -> dict[tuple[str, int], list[dict]]:
    """Group the append-only log by (system, run_index) for one model.

    Keying on the model is load-bearing: two models were graded as `full_agent`
    at `run_index` 0, so without it the later sweep silently replaces the earlier
    one and the figures show a different model than the caption claims.
    """
    path = path or RESULTS_DIR / "runs.jsonl"
    grouped: dict[tuple[str, int], dict[str, dict]] = defaultdict(dict)
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            # Deterministic baselines have no model; they are shared by all.
            if record.get("model") not in (None, model):
                continue
            key = (record["system"], record.get("run_index", 0))
            # Within one model, later lines win: a rerun appends rather than
            # replacing, so the newest record for a submission is the live one.
            grouped[key][record["submission_id"]] = record
    return {key: list(values.values()) for key, values in grouped.items()}


def _truth(submissions) -> dict[str, dict]:
    rubric = load_rubric()
    return {
        s.submission_id: {
            "label": s.true_label.value if s.true_label else None,
            "band": band_for(s.true_score or 0.0, rubric),
            "score": s.true_score or 0.0,
        }
        for s in submissions
    }


def risk_coverage(runs, truth) -> Path:
    """Accuracy as a function of how much of the set is auto-graded."""
    fig, ax = plt.subplots(figsize=(6.4, 4.0), dpi=160)

    for system in ("full_agent", "zero_shot_llm"):
        records = runs.get((system, 0))
        if not records:
            continue
        ordered = sorted(
            (r for r in records if r["submission_id"] in truth),
            key=lambda r: (r.get("diagnosis") or {}).get("confidence", 0.0),
            reverse=True,
        )
        xs, ys, correct = [], [], 0
        for index, record in enumerate(ordered, start=1):
            correct += record["score"]["band"] == truth[record["submission_id"]]["band"]
            xs.append(index / len(ordered))
            ys.append(correct / index)
        ax.plot(xs, ys, color=SERIES[system], linewidth=2.0, label=LABELS[system])

    ax.axvline(0.70, color=INK, linestyle=":", linewidth=1.0)
    ax.text(0.705, 0.06, "70% coverage", color=INK, fontsize=8, rotation=90)
    ax.set_ylim(0, 1.02)
    ax.set_xlim(0, 1)
    _style(
        ax,
        "Risk-coverage: accuracy over the most-confident fraction",
        "Coverage (fraction auto-graded)",
        "Band accuracy",
    )
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    return _save(fig, "risk_coverage.png")


def per_class_f1(runs, truth) -> Path:
    """Where the macro-F1 comes from, and which classes are too small to trust."""
    order, series = None, {}
    for system in ("full_agent", "zero_shot_llm"):
        records = runs.get((system, 0))
        if not records:
            continue
        pairs = [
            (
                Misconception(truth[r["submission_id"]]["label"]),
                Misconception((r.get("diagnosis") or {}).get("label"))
                if (r.get("diagnosis") or {}).get("label")
                else None,
            )
            for r in records
            if r["submission_id"] in truth and truth[r["submission_id"]]["label"]
        ]
        scores = metrics.per_class_f1([t for t, _ in pairs], [p for _, p in pairs])
        if order is None:
            order = sorted(scores, key=lambda k: -scores[k]["support"])
        series[system] = scores

    fig, ax = plt.subplots(figsize=(7.6, 4.0), dpi=160)
    width = 0.38
    positions = range(len(order))
    for offset, (system, scores) in enumerate(series.items()):
        ax.bar(
            [p + offset * width for p in positions],
            [scores[label]["f1"] for label in order],
            width=width,
            color=SERIES[system],
            label=LABELS[system],
        )
    ax.set_xticks([p + width / 2 for p in positions])
    ax.set_xticklabels(
        [f"{label}\nn={int(series[next(iter(series))][label]['support'])}" for label in order],
        fontsize=7.5,
        color=INK,
    )
    ax.set_ylim(0, 1.05)
    _style(ax, "Per-class diagnosis F1 (ordered by support)", "", "F1")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    return _save(fig, "per_class_f1.png")


def confusion(runs, truth) -> Path:
    """Which misconceptions get conflated by the full agent."""
    records = runs.get(("full_agent", 0), [])
    pairs = [
        (truth[r["submission_id"]]["label"], (r.get("diagnosis") or {}).get("label") or "NONE")
        for r in records
        if r["submission_id"] in truth and truth[r["submission_id"]]["label"]
    ]
    labels = sorted({t for t, _ in pairs} | {p for _, p in pairs if p != "NONE"})
    counts = Counter(pairs)
    grid = [[counts.get((t, p), 0) for p in labels] for t in labels]

    fig, ax = plt.subplots(figsize=(6.6, 5.6), dpi=160)
    ax.imshow(grid, cmap="Blues", vmin=0)
    ax.set_xticks(range(len(labels)), labels, fontsize=7.5, rotation=90, color=INK)
    ax.set_yticks(range(len(labels)), labels, fontsize=7.5, color=INK)
    for row in range(len(labels)):
        for column in range(len(labels)):
            value = grid[row][column]
            if value:
                ax.text(
                    column,
                    row,
                    str(value),
                    ha="center",
                    va="center",
                    fontsize=7.5,
                    color="white" if value > max(max(grid)) * 0.55 else INK,
                )
    ax.set_title(
        "Full agent: true label (rows) vs predicted (columns)", color=INK, fontsize=11, pad=10
    )
    ax.set_xlabel("Predicted", color=INK, fontsize=9)
    ax.set_ylabel("True", color=INK, fontsize=9)
    fig.tight_layout()
    return _save(fig, "confusion_matrix.png")


def false_positives(runs, truth) -> Path:
    """The number that matters most: correct work graded as buggy."""
    systems, rates = [], []
    for system in ("test_only", "static_only", "zero_shot_llm", "full_agent"):
        records = runs.get((system, 0))
        if not records:
            continue
        correct = [
            r
            for r in records
            if r["submission_id"] in truth
            and truth[r["submission_id"]]["label"] in {m.value for m in CORRECT_LABELS}
        ]
        if not correct:
            continue
        flagged = sum(
            1
            for r in correct
            if (r.get("diagnosis") or {}).get("label") not in {m.value for m in CORRECT_LABELS}
        )
        systems.append(LABELS[system])
        rates.append(flagged / len(correct))

    fig, ax = plt.subplots(figsize=(5.8, 3.4), dpi=160)
    bars = ax.bar(
        systems,
        rates,
        color=[SERIES[k] for k in ("test_only", "static_only", "zero_shot_llm", "full_agent")][
            : len(systems)
        ],
    )
    for bar, rate in zip(bars, rates, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            rate + 0.004,
            f"{rate:.1%}",
            ha="center",
            fontsize=9,
            color=INK,
        )
    ax.set_ylim(0, max(rates + [0.05]) * 1.35)
    _style(ax, "False-positive rate on correct submissions (OK / ALT)", "", "Flagged as buggy")
    ax.tick_params(axis="x", labelsize=8.5)
    return _save(fig, "false_positive_rate.png")


def _save(fig, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / name
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=HEADLINE_MODEL)
    args = parser.parse_args()

    runs = load_runs(model=args.model)
    truth = _truth(load_submissions())
    print(f"model: {args.model}")
    print(f"loaded {sum(len(v) for v in runs.values())} records across {len(runs)} runs")
    for builder in (risk_coverage, per_class_f1, confusion, false_positives):
        print(f"  wrote {builder(runs, truth).relative_to(RESULTS_DIR.parent)}")


if __name__ == "__main__":
    main()
