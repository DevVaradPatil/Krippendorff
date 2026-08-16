"""The core evaluation loop. Build this before the agent.

Reads a labelled submission set, runs one *system* over it (a baseline or the
full agent), writes append-only JSONL to ``results/``, and prints the metrics
table. Every number in the final report comes out of this file, which is why
week 1's deliverable is a working harness and a test-only baseline number
rather than a working agent.

Usage:
    python -m eval.harness --config eval/configs/default.yaml
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import yaml

from agent.schemas import SCHEMA_VERSION, GradingResult, Submission
from eval import metrics

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
DEFAULT_DATASET = ROOT / "data" / "synthetic" / "submissions.jsonl"


class System(Protocol):
    """Anything gradeable: each baseline and the full agent implements this."""

    name: str

    def grade(self, submission: Submission) -> GradingResult: ...


def load_submissions(path: Path = DEFAULT_DATASET) -> list[Submission]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found -- run `python -m data.mutations.generate` first"
        )
    with path.open(encoding="utf-8") as handle:
        submissions = [Submission(**json.loads(line)) for line in handle if line.strip()]

    stale = {s.schema_version for s in submissions} - {SCHEMA_VERSION}
    if stale:
        raise ValueError(
            f"dataset was written under schema {sorted(stale)} but the code is on "
            f"{SCHEMA_VERSION}. Regenerate it; stale records silently poison metrics."
        )
    return submissions


def run(
    system: System,
    submissions: Iterable[Submission],
    *,
    n_runs: int = 1,
    workers: int = 6,
    out: Path | None = None,
) -> list[list[GradingResult]]:
    """Grade every submission `n_runs` times; `n_runs` > 1 feeds C1."""
    submissions = list(submissions)
    runs: list[list[GradingResult]] = []

    for run_index in range(n_runs):
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            results = list(pool.map(system.grade, submissions))
        runs.append(results)
        print(
            f"  {system.name} run {run_index + 1}/{n_runs}: "
            f"{len(results)} submissions in {time.monotonic() - started:.1f}s"
        )

    if out is not None:
        _append_jsonl(out, system, runs)
    return runs


def _append_jsonl(path: Path, system: System, runs: list[list[GradingResult]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).isoformat()
    with path.open("a", encoding="utf-8") as handle:
        for run_index, results in enumerate(runs):
            for result in results:
                record = result.model_dump(mode="json")
                record.update(system=system.name, run_index=run_index, run_at=stamp)
                handle.write(json.dumps(record) + "\n")


def evaluate(runs: list[list[GradingResult]], submissions: list[Submission]) -> dict[str, object]:
    """Every headline metric for one system, on one dataset."""
    results = runs[0]
    true_labels = [s.true_label for s in submissions if s.true_label]
    predicted = [r.diagnosis.label if r.diagnosis else None for r in results]

    summary: dict[str, object] = {"n": len(results)}
    summary.update(metrics.band_accuracy(results, submissions))
    summary["macro_f1"] = metrics.macro_f1(true_labels, predicted)
    summary["fp_rate_on_correct"] = metrics.false_positive_rate_on_correct(true_labels, predicted)
    summary["accuracy_at_70pct_coverage"] = metrics.accuracy_at_coverage(results, submissions, 0.70)
    summary["ece"] = metrics.expected_calibration_error(results, submissions)
    summary.update(metrics.self_agreement(runs))
    summary.update(metrics.operational_summary(results))
    return summary


def run_and_report(
    system_names: list[str],
    *,
    dataset: Path = DEFAULT_DATASET,
    n_runs: int = 1,
    limit: int | None = None,
    out: Path | None = None,
) -> dict[str, dict]:
    from eval import baselines

    submissions = load_submissions(dataset)
    if limit:
        submissions = submissions[:limit]
    print(f"dataset: {len(submissions)} labelled submissions from {dataset}\n")

    out = out or RESULTS_DIR / "runs.jsonl"
    summaries: dict[str, dict] = {}
    for name in system_names:
        try:
            system = baselines.build(name, submissions)
        except NotImplementedError as exc:
            print(f"  {name}: not implemented yet ({exc})")
            continue
        try:
            runs = run(system, submissions, n_runs=n_runs, out=out)
        except NotImplementedError as exc:
            print(f"  {name}: not implemented yet ({exc})")
            continue
        summaries[name] = evaluate(runs, submissions)

    _print_table(summaries)
    return summaries


_COLUMNS = [
    ("band_accuracy", "band acc"),
    ("mean_band_distance", "band dist"),
    ("mean_score_error", "score err"),
    ("macro_f1", "macro-F1"),
    ("fp_rate_on_correct", "FP on OK/ALT"),
    ("accuracy_at_70pct_coverage", "acc@70%"),
    ("ece", "ECE"),
    ("exact_match_rate", "self-agree"),
]


def _print_table(summaries: dict[str, dict]) -> None:
    if not summaries:
        return
    header = f"\n{'system':<16}" + "".join(f"{label:>14}" for _, label in _COLUMNS)
    print(header)
    print("-" * len(header.strip("\n")))
    for name, summary in summaries.items():
        row = f"{name:<16}"
        for key, _ in _COLUMNS:
            value = summary.get(key)
            row += f"{value:>14.3f}" if isinstance(value, (int, float)) else f"{'-':>14}"
        print(row)
    print(
        f"\nhuman baseline for reference: self-disagreement "
        f"{metrics.HUMAN_SELF_DISAGREEMENT_BANDS} bands, inter-rater alpha "
        f"{metrics.HUMAN_INTERRATER_ALPHA_CORRECTNESS} (Messer et al. 2025)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "eval" / "configs" / "default.yaml")
    parser.add_argument("--systems", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--n-runs", type=int, default=None)
    args = parser.parse_args()

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    systems = args.systems or config.get("systems", ["test_only"])
    n_runs = args.n_runs if args.n_runs is not None else config.get("n_runs", 1)

    summaries = run_and_report(
        systems,
        dataset=ROOT / config.get("dataset", "data/synthetic") / "submissions.jsonl",
        n_runs=n_runs,
        limit=args.limit,
    )
    summary_path = RESULTS_DIR / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"\nwrote {summary_path}")


if __name__ == "__main__":
    main()
