"""Shared data contracts.

Everything crossing a stage boundary (S0-S7), every on-disk record in
``data/synthetic/``, and every row the eval harness reads is one of these
models. Changing a field changes the on-disk format: bump ``SCHEMA_VERSION``.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "0.1.0"


class Misconception(StrEnum):
    """The 14-class label space for C2 (spec section 3).

    ``OK`` and ``ALT`` are *correct* submissions. They are the false-positive
    tests and must stay at ~20% of the generated set.
    """

    OBO = "OBO"  # off-by-one
    CMP = "CMP"  # wrong comparison operator
    ACC = "ACC"  # accumulator initialised wrong
    DIV = "DIV"  # integer vs float division
    MUT = "MUT"  # mutable default argument
    ALI = "ALI"  # aliasing / shallow copy
    SCP = "SCP"  # scope / global misuse
    REC = "REC"  # missing or wrong recursive base case
    LOOP = "LOOP"  # early return inside a loop
    CONV = "CONV"  # missing convergence check
    EDGE = "EDGE"  # unhandled edge case
    TYPE = "TYPE"  # type confusion
    OK = "OK"  # correct, stylistically poor
    ALT = "ALT"  # correct via a different valid approach


CORRECT_LABELS = frozenset({Misconception.OK, Misconception.ALT})


class Span(BaseModel):
    """A 1-indexed, inclusive line range in the student's source file.

    Spans are mandatory on every diagnosis and are validated against the actual
    file before a diagnosis is accepted (CLAUDE.md invariant 3).
    """

    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> Span:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class Submission(BaseModel):
    """One student submission plus, for synthetic data, its ground truth."""

    submission_id: str
    problem_id: str
    source: str
    # Ground truth is present only for synthetic and mutation-derived data. It is
    # derived by rule from the applied mutation, never from a model or a grader.
    true_label: Misconception | None = None
    true_score: float | None = None
    mutation_id: str | None = None
    provenance: str = "synthetic"  # synthetic | menagerie | codeworkout | course
    schema_version: str = SCHEMA_VERSION


class TestResult(BaseModel):
    """One test case executed inside the sandbox (S1)."""

    test_id: str
    passed: bool
    kind: str = "normal"  # normal | edge | boundary | degenerate
    stdout: str = ""
    traceback: str | None = None
    duration_s: float = 0.0
    timed_out: bool = False


class StaticFeatures(BaseModel):
    """Deterministic style and complexity features (S2)."""

    ruff_violations: dict[str, int] = Field(default_factory=dict)
    cyclomatic_complexity: float | None = None
    maintainability_index: float | None = None
    function_count: int = 0
    docstring_coverage: float = 0.0
    comment_ratio: float = 0.0
    loc: int = 0


class Diagnosis(BaseModel):
    """The only LLM judgment in the scoring path (S4).

    Note what is absent: no correctness score. Correctness comes from
    ``TestResult`` alone, which is what keeps injections out of the largest
    score component.
    """

    label: Misconception
    evidence: list[Span] = Field(min_length=1)
    rationale: str
    subjective_scores: dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)


class Score(BaseModel):
    """Aggregated rubric outcome (S5). Weights come from rubric/rubric.yaml."""

    correctness: float  # from S1 only
    style: float  # from S2 only
    design: float  # from S4
    total: float
    band: str


class Route(StrEnum):
    AUTO = "auto"
    HUMAN_REVIEW = "human_review"


class GradingResult(BaseModel):
    """The pipeline's output record; one JSONL line under ``results/``."""

    submission_id: str
    score: Score
    diagnosis: Diagnosis | None = None
    route: Route = Route.AUTO
    route_reason: str | None = None
    consistency_samples: list[str] = Field(default_factory=list)
    adversarial_flags: list[str] = Field(default_factory=list)
    feedback: str | None = None
    model: str | None = None
    tokens: int | None = None
    cost_inr: float | None = None
    latency_s: float | None = None
    schema_version: str = SCHEMA_VERSION
