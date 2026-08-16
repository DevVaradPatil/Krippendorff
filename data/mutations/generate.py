"""Generate the labelled synthetic set.

For each problem: parse the reference solution, apply every applicable operator
at every site it matches, run the resulting variant in the sandbox to see which
tests it actually breaks, derive the rubric score by rule, and write a
``Submission`` to ``data/synthetic/``.

Two filters keep the ground truth honest:

**Equivalent mutants are discarded.** A mutation that passes the entire suite has
not produced a buggy submission -- it has produced a correct one that happens to
differ from the reference. Labelling it `OBO` would mean training and scoring the
agent against something that is not there. They are counted and reported rather
than silently dropped.

**OK and ALT variants must pass every test.** If a supposedly-correct variant
fails, the transformation was buggy, and keeping it would corrupt the
false-positive rate -- the single most important number in C2.

Usage:
    python -m data.mutations.generate --out data/synthetic
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from agent import static_analysis, static_gate
from agent.aggregate import aggregate, load_rubric
from agent.sandbox import SandboxLimits, run_tests
from agent.schemas import CORRECT_LABELS, Misconception, Submission
from data.mutations import style_ops
from data.mutations.operators import REGISTRY, Mutant, apply_edits
from data.problems.loader import Problem, load_all

OUT_DIR = Path(__file__).resolve().parent.parent / "synthetic"

#: Cap per (problem, operator) so one heavily-matched operator cannot dominate.
MAX_SITES_PER_OPERATOR = 6

#: Target share of OK/ALT in the finished set (spec section 3: "~20%").
#: Correct variants are cheap to produce and would otherwise swamp the set, so
#: the surplus is subsampled deterministically rather than generated blind.
CORRECT_TARGET_FRACTION = 0.20


@dataclass
class GenerationStats:
    kept: int = 0
    equivalent: int = 0
    gate_failed: int = 0
    broken_correct_variant: int = 0
    subsampled_correct: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "kept": self.kept,
            "discarded_equivalent_mutants": self.equivalent,
            "discarded_gate_failures": self.gate_failed,
            "discarded_broken_ok_alt": self.broken_correct_variant,
            "subsampled_correct_variants": self.subsampled_correct,
        }


def candidates(problem: Problem) -> list[Mutant]:
    """Every mutant the operators can produce for this problem, before testing."""
    import ast

    tree = ast.parse(problem.reference)
    applicable = set(problem.applicable)
    out: list[Mutant] = []
    # Two rules can land on the same site -- `range(len(x) - 1)` matches both
    # halves of the off-by-one operator. Identical sources are one mutant.
    seen_sources: set[str] = {problem.reference}

    for operator in REGISTRY.values():
        if operator.label not in applicable:
            continue
        try:
            sites = operator.find(tree, problem.reference)
        except (SyntaxError, ValueError, IndexError):
            continue
        kept_for_operator = 0
        for index, edits in enumerate(sites):
            if kept_for_operator >= MAX_SITES_PER_OPERATOR:
                break
            source, spans = apply_edits(problem.reference, edits)
            if source in seen_sources:
                continue
            seen_sources.add(source)
            kept_for_operator += 1
            out.append(
                Mutant(
                    operator_id=f"{operator.id}#{index}",
                    label=operator.label,
                    source=source,
                    sites=spans,
                    note=operator.description,
                )
            )

    if Misconception.OK in applicable:
        for variant_id, source in style_ops.ok_variants(problem.reference):
            out.append(
                Mutant(
                    operator_id=variant_id,
                    label=Misconception.OK,
                    source=source,
                    sites=[],
                    note="correct, presentation degraded",
                )
            )
    if Misconception.ALT in applicable and problem.alternative:
        out.append(
            Mutant(
                operator_id="alt_reference_implementation",
                label=Misconception.ALT,
                source=problem.alternative,
                sites=[],
                note="correct by a different approach",
            )
        )
    return out


def _evaluate(problem: Problem, mutant: Mutant, *, limits: SandboxLimits):
    """Run one mutant's tests. Returns (mutant, results) or (mutant, None)."""
    gate = static_gate.check(mutant.source)
    if not gate.passed:
        return mutant, None
    return mutant, run_tests(mutant.source, problem.tests_path, limits)


def generate(
    out_dir: Path = OUT_DIR,
    *,
    seed: int = 0,
    workers: int = 6,
    limits: SandboxLimits | None = None,
) -> tuple[list[Submission], GenerationStats]:
    limits = limits or SandboxLimits()
    rubric = load_rubric()
    rng = random.Random(seed)
    stats = GenerationStats()
    submissions: list[Submission] = []

    for problem in load_all():
        mutants = candidates(problem)
        # partial, not a closure: a lambda would capture `problem` by reference
        # and every worker would see whichever problem the loop had reached.
        evaluate_one = partial(_evaluate, problem, limits=limits)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            evaluated = list(pool.map(evaluate_one, mutants))

        for mutant, results in evaluated:
            if results is None:
                stats.gate_failed += 1
                continue
            all_passed = all(r.passed for r in results)
            is_correct_label = mutant.label in CORRECT_LABELS

            if is_correct_label and not all_passed:
                # The transformation was supposed to preserve behaviour and did
                # not. Discard it rather than mislabel a broken submission.
                stats.broken_correct_variant += 1
                continue
            if not is_correct_label and all_passed:
                stats.equivalent += 1
                continue

            features = static_analysis.extract(mutant.source)
            # Design is not varied by these operators: a wrong loop bound is an
            # implementation defect, not a design one. Held at 1.0 and reported
            # as a limitation of the synthetic set.
            score = aggregate(results, features, design=1.0, rubric=rubric)

            submissions.append(
                Submission(
                    submission_id=f"{problem.id}::{mutant.operator_id}",
                    problem_id=problem.id,
                    source=mutant.source,
                    true_label=mutant.label,
                    true_score=score.total,
                    mutation_id=mutant.operator_id,
                    provenance="synthetic",
                )
            )
            stats.kept += 1

    submissions = _balance_correct(submissions, rng, stats)
    rng.shuffle(submissions)
    _write(submissions, out_dir)
    return submissions, stats


def _balance_correct(
    submissions: list[Submission], rng: random.Random, stats: GenerationStats
) -> list[Submission]:
    """Trim OK/ALT down to roughly `CORRECT_TARGET_FRACTION` of the set.

    Sampling is stratified by problem so no problem loses all of its correct
    variants -- a per-problem false-positive rate is more informative than an
    aggregate one, and ALT is kept ahead of OK because it is the harder case.
    """
    correct = [s for s in submissions if s.true_label in CORRECT_LABELS]
    buggy = [s for s in submissions if s.true_label not in CORRECT_LABELS]
    if not buggy:
        return submissions

    target = round(len(buggy) * CORRECT_TARGET_FRACTION / (1 - CORRECT_TARGET_FRACTION))
    if len(correct) <= target:
        return submissions

    by_problem: dict[str, list[Submission]] = {}
    for submission in correct:
        by_problem.setdefault(submission.problem_id, []).append(submission)
    for group in by_problem.values():
        # ALT first, then a stable shuffle of the OK variants.
        rng.shuffle(group)
        group.sort(key=lambda s: s.true_label != Misconception.ALT)

    kept: list[Submission] = []
    round_index = 0
    while len(kept) < target:
        added = False
        for group in by_problem.values():
            if round_index < len(group) and len(kept) < target:
                kept.append(group[round_index])
                added = True
        if not added:
            break
        round_index += 1

    stats.subsampled_correct = len(correct) - len(kept)
    return buggy + kept


def _write(submissions: list[Submission], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "submissions.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for submission in submissions:
            handle.write(submission.model_dump_json() + "\n")


def label_distribution(submissions: list[Submission]) -> Counter:
    return Counter(s.true_label.value for s in submissions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    submissions, stats = generate(args.out, seed=args.seed, workers=args.workers)
    distribution = label_distribution(submissions)
    correct = sum(distribution[label] for label in ("OK", "ALT"))

    print(json.dumps(stats.as_dict(), indent=2))
    print(f"\n{len(submissions)} submissions written to {args.out}")
    print(f"correct (OK+ALT): {correct} = {correct / max(1, len(submissions)):.1%}\n")
    for label, count in distribution.most_common():
        print(f"  {label:5s} {count:4d}")


if __name__ == "__main__":
    main()
