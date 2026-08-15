"""The rubric is data, and several invariants depend on it staying well-formed."""

from __future__ import annotations

from pathlib import Path

import yaml

RUBRIC = Path(__file__).resolve().parent.parent / "rubric" / "rubric.yaml"


def load():
    return yaml.safe_load(RUBRIC.read_text(encoding="utf-8"))


def test_weights_sum_to_one():
    rubric = load()
    total = sum(c["weight"] for c in rubric["criteria"].values())
    assert abs(total - 1.0) < 1e-9


def test_llm_cannot_own_correctness_or_style():
    # Invariant: S4 output may never feed these criteria. If a rubric edit
    # moves either to S4, the injection defense and the variance argument both
    # collapse, so fail loudly here.
    criteria = load()["criteria"]
    assert "S4" not in criteria["correctness"]["source"]
    assert "S4" not in criteria["style"]["source"]


def test_bands_are_descending_and_cover_zero():
    bands = load()["bands"]
    mins = [b["min"] for b in bands]
    assert mins == sorted(mins, reverse=True)
    assert mins[-1] == 0.0
