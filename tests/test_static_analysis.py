"""S2 feature extraction, including the encodings students actually produce."""

from __future__ import annotations

import pytest

from agent.static_analysis import extract

CLEAN = '''"""Doc."""


def total(values):
    """Sum them."""
    result = 0
    for value in values:
        result = result + value
    return result
'''


def test_basic_features():
    features = extract(CLEAN)
    assert features.function_count == 1
    assert features.docstring_coverage == 1.0
    assert features.loc > 0
    assert features.cyclomatic_complexity is not None


@pytest.mark.parametrize(
    "snippet",
    [
        "# zero​width space in a comment\nx = 1\n",
        "# homоglyph: cyrillic o\nx = 1\n",
        "# emoji \U0001f600\nx = 1\n",
        'x = "café"\n',
    ],
)
def test_non_latin1_source_does_not_crash_the_pipeline(snippet):
    # Found by the C4 unicode attack family: ruff is invoked through a pipe, and
    # on Windows that pipe defaults to cp1252, so any character outside Latin-1
    # raised UnicodeEncodeError and took the grader down. An attack that crashes
    # the grader is an availability problem, not just a scoring one.
    features = extract(snippet)
    assert features.loc >= 1
