"""Generate the labelled synthetic set.

For each problem: parse the reference solution, apply every applicable operator,
run the resulting variant against the test suite to record which tests it
breaks, derive the score by rule, and write a ``Submission`` to
``data/synthetic/``.

Target 300-400 submissions across 25 problems, with OK/ALT held at ~20%.

An optional realism pass rewrites a subset through an LLM ("rewrite this as a
struggling first-year student would, keeping the bug") to add bad names, dead
code and stray prints. The label never changes in that pass; if the rewrite
alters behaviour, discard it rather than relabelling.

Usage:
    python -m data.mutations.generate --out data/synthetic --realism 0.3
"""

from __future__ import annotations

from pathlib import Path

from agent.schemas import Submission


def generate(problems_dir: Path, out_dir: Path, *, realism: float = 0.0,
             seed: int = 0) -> list[Submission]:
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
