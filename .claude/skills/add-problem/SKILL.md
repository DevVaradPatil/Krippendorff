---
name: add-problem
description: Add a new problem to the benchmark - spec, reference solution, and test suite - under data/problems/. Use when adding, authoring, or fixing one of the 25 intro-Python problems the synthetic set is generated from.
---

# Add a problem

Every synthetic submission is a mutation of some problem's reference solution, so
a weak problem quietly weakens every number derived from it. Work in this order.

## 1. Scope it

Pick from the course's actual topics: numerical integration, root finding, matrix
operations, series summation, prime sieves, string processing, file I/O,
recursion, simple plotting. Before writing, check `data/problems/` — an eighth
integration problem adds less than a first file-I/O one, because coverage of the
14 misconception codes is what the eval needs.

## 2. Create the directory

```
data/problems/<snake_case_id>/
├── problem.yaml
├── reference.py
└── tests.py
```

`problem.yaml` needs `id` (matching the directory), `title`, `statement`,
`misconceptions_applicable`, and `tags`. List only codes the problem can
genuinely express — a problem with no recursion cannot host `REC`, and forcing
it produces an unrealistic variant that inflates diagnosis F1.

## 3. Write `reference.py`

Mutation operators are **AST transforms applied to this file**, so it must be
mutable in the ways the taxonomy needs: a real accumulator for `ACC`, a genuine
`range` bound for `OBO`, a division that matters for `DIV`. Straight-line code
that calls a library one-liner is unmutatable. Keep it clean and idiomatic —
it is also the leak-detection target in S7 and the trusted context in S3.

## 4. Write `tests.py`

5–10 cases, each tagged `normal`, `edge`, `boundary`, or `degenerate`. At least
one `edge` and one `boundary`, always. Mutation severity is derived from *which
kinds* a mutation breaks, so a suite of only `normal` cases cannot separate an
edge-case bug from correct code, and the rule-derived ground-truth score
degrades for every variant of that problem.

Tests must be deterministic: no clock, no unseeded randomness, no network, no
file writes outside a tmp path. They run in a sandbox with no network and a 5s
timeout.

## 5. Verify before committing

- Reference passes every test.
- Hand-apply two or three applicable operators and confirm each breaks a
  different, sensible set of tests — if two misconceptions break exactly the
  same tests, the problem cannot distinguish them and the confusion matrix will
  show it later.
- Run `python -m data.mutations.generate` restricted to the new problem and
  eyeball the labels and derived scores.
