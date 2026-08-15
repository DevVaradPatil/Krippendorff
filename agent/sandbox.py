"""S1 - sandboxed execution.

Runs the student's code against the problem's test suite inside Docker with
``--network none``, a memory cap, a CPU cap, a hard wall-clock timeout and no
host mounts other than a read-only copy of the submission and tests.

Untrusted code is never executed in this process. There is no ``exec()``
fallback and no "just this once on the host" path -- if Docker is unavailable
the correct behaviour is to fail loudly, because the results of this stage are
the ground truth that the entire evaluation rests on.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent.schemas import TestResult


@dataclass(frozen=True)
class SandboxLimits:
    timeout_s: float = 5.0
    memory_mb: int = 256
    cpus: float = 1.0
    pids: int = 64
    image: str = "python:3.12-slim"


class SandboxUnavailableError(RuntimeError):
    """Raised when Docker is missing. Do not degrade to host execution."""


def run_tests(
    source: str,
    tests_path: Path,
    limits: SandboxLimits = SandboxLimits(),
) -> list[TestResult]:
    """Execute `source` against the test suite; one TestResult per test case."""
    raise NotImplementedError
