"""S4 - LLM diagnosis.

The single point in the scoring path where a model exercises judgment. It
answers only: which misconception, where in the code, how confident, and the
subjective rubric criteria. It is never asked whether the code is correct --
the tests already answered that.

Output is a ``Diagnosis``, enforced by schema with retries on parse failure.
Returned spans are validated against the real source; a diagnosis citing a
line that does not exist is rejected, not repaired.
"""

from __future__ import annotations

from agent.evidence import EvidenceBundle
from agent.schemas import Diagnosis


def diagnose(bundle: EvidenceBundle, *, model: str, run_index: int = 0) -> Diagnosis:
    """One structured diagnosis.

    `run_index` enters the cache key so N-sample consistency runs (S6) draw
    fresh completions instead of replaying one cached answer.
    """
    raise NotImplementedError


def validate_spans(diagnosis: Diagnosis, source: str) -> bool:
    """True if every evidence span lies within `source`."""
    raise NotImplementedError
