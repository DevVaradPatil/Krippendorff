"""Guards on the shared contract. These are cheap and catch silent corruption
of the label space or the on-disk format."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.schemas import CORRECT_LABELS, Misconception, Span


def test_taxonomy_is_the_specified_14_classes():
    expected = {"OBO", "CMP", "ACC", "DIV", "MUT", "ALI", "SCP", "REC",
                "LOOP", "CONV", "EDGE", "TYPE", "OK", "ALT"}
    assert {m.value for m in Misconception} == expected


def test_correct_labels_are_ok_and_alt():
    # These are the false-positive tests; treating either as a bug label would
    # silently make the most important C2 number meaningless.
    assert CORRECT_LABELS == {Misconception.OK, Misconception.ALT}


def test_spans_are_one_indexed_and_ordered():
    assert Span(start_line=1, end_line=1)
    with pytest.raises(ValidationError):
        Span(start_line=0, end_line=3)
    with pytest.raises(ValidationError):
        Span(start_line=5, end_line=2)
