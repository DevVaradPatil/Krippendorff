"""Guards on the mutation operators.

An operator that lies about its label, its site, or whether it applied at all
corrupts the ground truth, and nothing downstream can detect it. These tests are
deliberately about *provenance* rather than about generating good bugs.
"""

from __future__ import annotations

import ast

import pytest

from agent.schemas import CORRECT_LABELS, Misconception
from data.mutations import style_ops
from data.mutations.operators import REGISTRY, apply_edits
from data.problems.loader import load_all

SAMPLE = '''"""Doc."""


def total(values, seen=None):
    """Add them up."""
    if seen is None:
        seen = []
    if len(values) == 0:
        raise ValueError('empty')
    last = values[len(values) - 1]
    result = 0 * last
    for i in range(len(values)):
        if values[i] < 0:
            continue
        result = result + values[i] / 2
    return result
'''


def _mutants(operator_id: str, source: str = SAMPLE):
    operator = REGISTRY[operator_id]
    edits = operator.find(ast.parse(source), source)
    return [apply_edits(source, e) for e in edits]


def test_every_operator_declares_a_taxonomy_label():
    for operator in REGISTRY.values():
        assert operator.label in Misconception
        assert operator.label not in CORRECT_LABELS, (
            f"{operator.id} claims a correct label; OK/ALT come from style_ops"
        )


@pytest.mark.parametrize("operator_id", sorted(REGISTRY))
def test_mutants_still_parse(operator_id):
    # A mutant that no longer parses is caught by S0 and never reaches
    # diagnosis, so it tests nothing about misconception identification.
    for source, _ in _mutants(operator_id):
        ast.parse(source)


@pytest.mark.parametrize("operator_id", sorted(REGISTRY))
def test_mutants_differ_from_the_original(operator_id):
    for source, _ in _mutants(operator_id):
        assert source != SAMPLE


@pytest.mark.parametrize("operator_id", sorted(REGISTRY))
def test_spans_point_inside_the_mutated_file(operator_id):
    for source, spans in _mutants(operator_id):
        line_count = len(source.splitlines())
        for span in spans:
            assert 1 <= span.start_line <= line_count
            assert span.end_line <= line_count


def test_operator_declines_when_it_does_not_apply():
    # No recursion in SAMPLE, so the base-case operator must find nothing
    # rather than force a mutation into a problem that cannot express it.
    assert _mutants("rec_missing_base_case") == []


def test_obo_finds_both_range_and_len_sites():
    assert len(_mutants("obo_range_bound")) >= 2


def test_mutable_default_edits_both_signature_and_guard():
    mutants = _mutants("mut_default_arg")
    assert len(mutants) == 1
    source, _ = mutants[0]
    assert "seen=[]" in source.replace(" ", "")
    assert "is None" not in source


class TestCorrectVariants:
    """OK/ALT must preserve behaviour: they are the false-positive tests."""

    def test_stripping_comments_keeps_the_code(self):
        stripped = style_ops.strip_comments_and_docstrings(SAMPLE)
        assert "Doc." not in stripped
        assert "Add them up." not in stripped
        assert "result = result + values[i] / 2" in stripped
        ast.parse(stripped)

    def test_renaming_never_collides_with_an_existing_name(self):
        # Renaming `result` to `a` in a function that already has a parameter
        # `a` changes behaviour, producing an "OK" sample that fails its tests.
        renamed = style_ops.rename_locals(SAMPLE)
        tree = ast.parse(renamed)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef))
        names = [a.arg for a in function.args.args] + [
            n.id
            for n in ast.walk(function)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        ]
        assert len(set(names)) == len(set(dict.fromkeys(names)))
        assert len([a.arg for a in function.args.args]) == len(
            set(a.arg for a in function.args.args)
        )

    def test_ok_variants_are_syntactically_valid(self):
        for _, source in style_ops.ok_variants(SAMPLE):
            ast.parse(source)


def test_every_problem_declares_applicable_labels_it_can_express():
    # A problem claiming a code no operator can find inflates the expected
    # label distribution and silently under-fills that class.
    for problem in load_all():
        tree = ast.parse(problem.reference)
        for label in problem.applicable:
            if label in CORRECT_LABELS:
                continue
            operators = [op for op in REGISTRY.values() if op.label == label]
            found = any(op.find(tree, problem.reference) for op in operators)
            assert found, f"{problem.id} declares {label.value} but no operator matches"
