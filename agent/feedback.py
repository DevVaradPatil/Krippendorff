"""S7 - feedback generation and leak detection.

Socratic, targeted at the diagnosed misconception, grounded in the evidence
spans from S4, and containing no part of the reference solution. The leak
detector runs after generation and before the text is returned: exact substring
match plus n-gram overlap against the reference. A leak is a hard failure --
regenerate or fall back to a template, never ship the text.
"""

from __future__ import annotations

from agent.schemas import Diagnosis

NGRAM_SIZE = 8
MAX_OVERLAP_RATIO = 0.15


def generate(diagnosis: Diagnosis, source: str, *, model: str) -> str:
    raise NotImplementedError


def leaks_solution(feedback: str, reference_solution: str) -> bool:
    """True if `feedback` reproduces the reference beyond the allowed overlap."""
    raise NotImplementedError
