"""S3 - evidence bundle.

Assembles exactly what S4 is allowed to see, and separates trusted context from
untrusted student input.

Trusted: problem statement, rubric, reference solution, test results, static
features. Untrusted: the student's source, and -- held apart from it -- the
comments and docstrings stripped out of that source. Injections overwhelmingly
live in comments, so they are removed from the code the model reads and passed
as clearly-labelled untrusted data, or dropped entirely under strict defenses.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from agent.schemas import StaticFeatures, TestResult


@dataclass
class EvidenceBundle:
    problem_statement: str
    rubric_yaml: str
    reference_solution: str
    student_code_stripped: str
    student_comments: list[str] = field(default_factory=list)
    test_results: list[TestResult] = field(default_factory=list)
    static_features: StaticFeatures | None = None
    # Line map from stripped source back to original line numbers, so evidence
    # spans returned by the model point at the file the student actually wrote.
    line_map: dict[int, int] = field(default_factory=dict)


def strip_comments(source: str) -> tuple[str, list[str], dict[int, int]]:
    """Return (code without comments/docstrings, extracted text, line map)."""
    raise NotImplementedError


def build(*, problem_id: str, source: str, results: list[TestResult],
          features: StaticFeatures) -> EvidenceBundle:
    raise NotImplementedError
