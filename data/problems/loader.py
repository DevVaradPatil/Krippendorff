"""Load problem definitions from disk.

A problem directory holds the trusted half of the evaluation: the statement the
model is allowed to see, the reference solution that mutations are applied to,
the test suite that decides correctness, and optionally a genuinely different
correct implementation used to generate `ALT` submissions.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from agent.schemas import Misconception

PROBLEMS_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Problem:
    id: str
    title: str
    statement: str
    tags: list[str]
    applicable: list[Misconception]
    reference: str
    tests_path: Path
    alternative: str | None  # a different correct solution, for ALT

    @property
    def tests_source(self) -> str:
        return self.tests_path.read_text(encoding="utf-8")


def load_problem(directory: Path) -> Problem:
    meta = yaml.safe_load((directory / "problem.yaml").read_text(encoding="utf-8"))
    if meta["id"] != directory.name:
        raise ValueError(f"{directory}: id {meta['id']!r} must match directory name")

    alternative = directory / "alternative.py"
    return Problem(
        id=meta["id"],
        title=meta["title"],
        statement=meta["statement"].strip(),
        tags=meta.get("tags", []),
        applicable=[Misconception(c) for c in meta.get("misconceptions_applicable", [])],
        reference=(directory / "reference.py").read_text(encoding="utf-8"),
        tests_path=directory / "tests.py",
        alternative=alternative.read_text(encoding="utf-8") if alternative.exists() else None,
    )


@cache
def load_all(root: Path = PROBLEMS_DIR) -> tuple[Problem, ...]:
    return tuple(
        load_problem(d)
        for d in sorted(Path(root).iterdir())
        if d.is_dir() and (d / "problem.yaml").exists()
    )
