"""S2 - deterministic feature extraction.

ruff for style violations, radon for complexity and maintainability, `ast` for
structural metrics. Everything the style rubric criterion needs comes from here
and from nowhere else -- the LLM is never asked to judge style.
"""

from __future__ import annotations

from agent.schemas import StaticFeatures


def extract(source: str) -> StaticFeatures:
    """Compute style and complexity features. No execution, no model call."""
    raise NotImplementedError
