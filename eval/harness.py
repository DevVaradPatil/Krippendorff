"""The core evaluation loop. Build this before the agent.

Reads a config, loads a labelled submission set, runs one *system* over it
(baseline or full agent), writes append-only JSONL to ``results/``, and hands
the records to ``eval.metrics``. Every number in the final report comes out of
this file, which is why week 1's deliverable is a working harness and a
test-only baseline number rather than a working agent.

Usage:
    python -m eval.harness --config eval/configs/default.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol

from agent.schemas import GradingResult, Submission

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


class System(Protocol):
    """Anything gradeable: each baseline and the full agent implements this."""

    name: str

    def grade(self, submission: Submission) -> GradingResult: ...


def load_submissions(path: Path) -> list[Submission]:
    raise NotImplementedError


def run(system: System, submissions: Iterable[Submission], *, n_runs: int = 1,
        out: Path | None = None) -> list[GradingResult]:
    """Grade every submission `n_runs` times; `n_runs` > 1 feeds C1."""
    raise NotImplementedError


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
