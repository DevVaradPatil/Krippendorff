"""Measure S7: leak rate, template-fallback rate, and what the text looks like.

Feedback never changes a grade, so it has no place in the C1-C3 tables. What it
does have is one measurable safety property -- how often generated text
reproduces the reference solution -- and one quality question a number cannot
answer, so this prints samples for a human to read.

Usage:
    python -m eval.feedback_run --n 15 --model primary
"""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path

import yaml

from agent import evidence as s3
from agent import feedback as s7
from agent import static_analysis as s2
from agent.diagnose import diagnose
from agent.llm import USAGE, load_model_config
from agent.sandbox import run_tests
from agent.schemas import CORRECT_LABELS
from data.problems.loader import load_all
from eval.harness import RESULTS_DIR, ROOT, _load_dotenv, load_submissions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=15)
    parser.add_argument("--model", default="primary")
    parser.add_argument("--show", type=int, default=3, help="samples to print")
    parser.add_argument("--config", type=Path, default=ROOT / "eval" / "configs" / "default.yaml")
    args = parser.parse_args()

    _load_dotenv()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    model = load_model_config(config, args.model)

    problems = {p.id: p for p in load_all()}
    # Buggy submissions only: feedback on correct work is a different task, and
    # the leak risk lives where there is a fix to give away.
    targets = [s for s in load_submissions() if s.true_label not in CORRECT_LABELS][: args.n]

    print(f"model: {model.name}\n{len(targets)} submissions, 2 calls each worst case\n")

    records = []
    for submission in targets:
        problem = problems[submission.problem_id]
        results = run_tests(submission.source, problem.tests_path)
        bundle = s3.build(
            problem_id=problem.id,
            problem_statement=problem.statement,
            reference_solution=problem.reference,
            source=submission.source,
            results=results,
            features=s2.extract(submission.source),
        )
        diagnosis, _ = diagnose(bundle, model)
        text, used_template, _ = s7.generate(
            diagnosis,
            submission.source,
            results,
            problem.statement,
            problem.reference,
            model,
        )
        records.append(
            {
                "submission_id": submission.submission_id,
                "true_label": submission.true_label.value,
                "diagnosed": diagnosis.label.value,
                "used_template": used_template,
                "overlap_ratio": round(
                    s7.overlap_ratio(text, problem.reference, submission.source), 4
                ),
                "verbatim_lines": s7.verbatim_lines(text, problem.reference, submission.source),
                "leaked": s7.leaks_solution(text, problem.reference, submission.source),
                "feedback": text,
            }
        )

    leaked = sum(r["leaked"] for r in records)
    templated = sum(r["used_template"] for r in records)
    worst = max(r["overlap_ratio"] for r in records) if records else 0.0

    print(f"{'shipped with a leak':<34}{leaked}/{len(records)}")
    print(f"{'fell back to the template':<34}{templated}/{len(records)}")
    print(f"{'highest overlap ratio shipped':<34}{worst:.3f} (limit {s7.MAX_OVERLAP_RATIO})")
    print(f"\nmodel calls: {USAGE.calls} live, {USAGE.cache_hits} cached")

    for record in records[: args.show]:
        print(f"\n--- {record['submission_id']} ({record['true_label']}) ---")
        print(textwrap.fill(record["feedback"], 78, replace_whitespace=False))

    out = RESULTS_DIR / "feedback.json"
    out.write_text(json.dumps(records, indent=1), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
