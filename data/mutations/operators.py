"""Mutation operators - one per misconception, each carrying its ground truth.

This is where the evaluation's credibility comes from. Because we know exactly
which mutation was applied and which tests it breaks, the rubric score is
computed by rule (``agent.aggregate.aggregate``) rather than guessed at by a
human. Every operator must therefore declare its label and severity, and must
be an AST transform rather than a text substitution so the applied site is
known precisely and can be recorded as ground-truth evidence spans.

``OK`` and ``ALT`` are mutations too: they change the code without breaking it
(single-letter renames, comment removal, iterative-for-recursive rewrites) and
they are the false-positive tests. Keep them at ~20% of the generated set.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Callable

from agent.schemas import Misconception, Span


@dataclass(frozen=True)
class MutationOutcome:
    source: str
    label: Misconception
    severity: str  # minor | major | fatal -- feeds the rule-derived score
    sites: list[Span]


@dataclass(frozen=True)
class MutationOperator:
    id: str
    label: Misconception
    description: str
    apply: Callable[[ast.Module], MutationOutcome | None]


REGISTRY: dict[str, MutationOperator] = {}


def register(op: MutationOperator) -> MutationOperator:
    if op.id in REGISTRY:
        raise ValueError(f"duplicate mutation operator id: {op.id}")
    REGISTRY[op.id] = op
    return op


# One operator per row of the taxonomy table in the spec (section 3):
# OBO range(n) -> range(n-1) | CMP <= -> < | ACC total = 0 -> 1 | DIV / -> //
# MUT default arg -> [] | ALI b = a.copy() -> b = a | SCP local -> global
# REC drop base case | LOOP continue -> return | CONV tolerance -> fixed iters
# EDGE drop empty-input guard | TYPE float(input()) -> input()
# OK   rename to single letters, strip comments | ALT rewrite, still correct
