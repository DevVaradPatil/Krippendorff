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

from agent.confidence import RoutingPolicy
from agent.llm import USAGE, ModelConfig, load_model_config
from agent.schemas import SCHEMA_VERSION, GradingResult, Submission
from eval import metrics

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
DEFAULT_DATASET = ROOT / "data" / "synthetic" / "submissions.jsonl"


class System(Protocol):
    """Anything gradeable: each baseline and the full agent implements this."""

    name: str

    def grade(self, submission: Submission) -> GradingResult: ...


def _load_dotenv() -> None:
    """Load `.env` if present. Keys already in the environment win."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional convenience
        return
    load_dotenv(ROOT / ".env", override=False)


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
        # Without this, repeating a run would reuse the same per-sample cache
        # keys and replay identical answers, reporting perfect self-agreement
        # having never asked the model twice. C1 would be a fabrication.
        if hasattr(system, "run_offset"):
            system.run_offset = run_index
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
    model: ModelConfig | None = None,
    policy: RoutingPolicy | None = None,
    workers: int = 6,
) -> dict[str, dict]:
    from eval import baselines

    submissions = load_submissions(dataset)
    if limit:
        submissions = submissions[:limit]
    print(f"dataset: {len(submissions)} labelled submissions from {dataset}")
    if model:
        print(f"model:   {model.name} @ temperature {model.temperature}")
    print()

    out = out or RESULTS_DIR / "runs.jsonl"
    summaries: dict[str, dict] = {}
    for name in system_names:
        # LLM systems are slower and rate-limited; the deterministic ones are
        # not, so they do not share a worker count.
        is_llm = name in baselines.LLM_SYSTEMS
        try:
            system = baselines.build(name, submissions, model=model, policy=policy)
            runs = run(
                system,
                submissions,
                n_runs=n_runs,
                out=out,
                workers=4 if is_llm else workers,
            )
        except NotImplementedError as exc:
            print(f"  {name}: not available ({exc})")
            continue
        summaries[name] = evaluate(runs, submissions)
        if is_llm:
            print_diagnosis_detail(runs, submissions, name)

    _print_table(summaries)
    _print_usage()
    return summaries


def print_diagnosis_detail(
    runs: list[list[GradingResult]], submissions: list[Submission], name: str
) -> None:
    """Per-class F1 and the top confusions. Where the macro number comes from."""
    results = runs[0]
    true_labels = [s.true_label for s in submissions if s.true_label]
    predicted = [r.diagnosis.label if r.diagnosis else None for r in results]

    print(f"\n--- {name}: per-class diagnosis ---")
    print(f"{'label':<6}{'prec':>7}{'rec':>7}{'F1':>7}{'n':>5}")
    for label, scores in metrics.per_class_f1(true_labels, predicted).items():
        print(
            f"{label:<6}{scores['precision']:>7.2f}{scores['recall']:>7.2f}"
            f"{scores['f1']:>7.2f}{int(scores['support']):>5d}"
        )

    confusions = []
    for truth, counts in metrics.confusion_matrix(true_labels, predicted).items():
        for guess, count in counts.items():
            if guess != truth:
                confusions.append((count, truth, guess))
    if confusions:
        print("\ntop confusions (truth -> predicted):")
        for count, truth, guess in sorted(confusions, reverse=True)[:8]:
            print(f"  {truth:>4} -> {guess:<4} {count}")

    deferred = [r for r in results if r.route.value == "human_review"]
    print(f"\ndeferred to human review: {len(deferred)}/{len(results)}")
    reasons: dict[str, int] = {}
    for result in deferred:
        key = (result.route_reason or "?").split("(")[0].split(";")[0].strip()
        reasons[key] = reasons.get(key, 0) + 1
    for reason, count in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print(f"  {count:>3}  {reason}")


def _print_usage() -> None:
    if not USAGE.calls and not USAGE.cache_hits:
        return
    print(
        f"\nmodel calls: {USAGE.calls} live, {USAGE.cache_hits} cached, "
        f"{USAGE.parse_retries} schema retries · "
        f"tokens in/out: {USAGE.tokens_in}/{USAGE.tokens_out}"
    )


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


def _preview() -> None:
    """Show what S4 would actually be sent. Costs nothing, needs no key."""
    from agent import evidence, static_analysis
    from agent.diagnose import SYSTEM, build_prompt
    from agent.sandbox import run_tests
    from data.problems.loader import load_all

    submissions = load_submissions()
    problems = {p.id: p for p in load_all()}
    submission = next(s for s in submissions if s.true_label and s.true_label.value != "OK")
    problem = problems[submission.problem_id]

    bundle = evidence.build(
        problem_id=problem.id,
        problem_statement=problem.statement,
        reference_solution=problem.reference,
        source=submission.source,
        results=run_tests(submission.source, problem.tests_path),
        features=static_analysis.extract(submission.source),
    )
    prompt = build_prompt(bundle)
    print(f"=== submission {submission.submission_id} (truth: {submission.true_label.value})")
    print(f"=== system prompt ===\n{SYSTEM}\n")
    print(f"=== user prompt ===\n{prompt}\n")
    size = len(prompt) + len(SYSTEM)
    print(f"=== {size} chars, roughly {size // 4} tokens")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "eval" / "configs" / "default.yaml")
    parser.add_argument("--systems", nargs="*", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--n-runs", type=int, default=None)
    parser.add_argument(
        "--n-samples",
        type=int,
        default=None,
        help="S4 samples per submission; 1 costs a third as many calls",
    )
    parser.add_argument("--model", default="primary", help="key under `models:`")
    parser.add_argument(
        "--preview",
        action="store_true",
        help="print the exact S4 prompt for one submission and exit; no model call",
    )
    args = parser.parse_args()

    _load_dotenv()
    if args.preview:
        _preview()
        return
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    systems = args.systems or config.get("systems", ["test_only"])
    n_runs = args.n_runs if args.n_runs is not None else config.get("n_runs", 1)

    model = None
    if config.get("models", {}).get(args.model):
        model = load_model_config(config, args.model)

    routing = config.get("routing", {})
    policy = RoutingPolicy(
        n_samples=args.n_samples or routing.get("n_samples", 3),
        min_agreement=routing.get("min_agreement", 2 / 3),
        min_confidence=routing.get("min_confidence", 0.6),
        band_margin=routing.get("band_margin", 0.02),
    )

    summaries = run_and_report(
        systems,
        dataset=ROOT / config.get("dataset", "data/synthetic") / "submissions.jsonl",
        n_runs=n_runs,
        limit=args.limit,
        model=model,
        policy=policy,
    )
    summary_path = RESULTS_DIR / "summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(f"\nwrote {summary_path}")


if __name__ == "__main__":
    main()
