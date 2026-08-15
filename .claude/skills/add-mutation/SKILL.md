---
name: add-mutation
description: Add or change a mutation operator in data/mutations/operators.py, keeping its ground-truth label, severity, and evidence spans correct. Use when implementing a misconception from the taxonomy or fixing how a labelled bug is injected.
---

# Add a mutation operator

An operator is the ground truth for every submission it generates. If it lies
about its label, severity, or site, the C2 numbers are wrong and nothing
downstream can detect it.

## Rules

**AST transform, not text substitution.** A regex that turns `<=` into `<` will
hit a string literal or a comment sooner or later, mislabel the result, and
record a bogus evidence span. Transform the parsed tree, record the exact
`Span`s you touched, and unparse.

**Return `None` when inapplicable.** An operator that cannot find its target
must decline. Never force a mutation into a problem that does not express it —
that is how unrealistic variants enter the set and inflate F1.

**Severity is derived, not asserted.** Run the variant against the test suite and
set severity from which test kinds break. Do not hand-assign it.

**One label per operator.** If a transform can produce two different
misconceptions depending on where it lands, split it into two operators.

## Steps

1. Add the operator to `data/mutations/operators.py` and `register()` it — ids
   are unique and the registry rejects duplicates.
2. Confirm the label exists in `agent.schemas.Misconception`. The 14 classes are
   fixed by the spec; adding a fifteenth changes the label space and invalidates
   comparison with earlier runs, so raise it as a decision rather than doing it.
3. Add a test in `tests/` that applies the operator to a small fixture and
   asserts: the label, the evidence spans, and that the mutated code still
   *parses* (a syntax error would be caught by S0 and never reach diagnosis,
   which is a different experiment).
4. Regenerate and check the label distribution — `OK` and `ALT` must stay at
   roughly 20% of the set.

## `OK` and `ALT` are mutations too

They change the code without breaking it: single-letter renames and stripped
comments for `OK`, a valid rewrite (iterative for recursive, comprehension for
loop) for `ALT`. Their generated variants **must still pass every test** —
assert that in the test. These two produce the most important number in the
evaluation, the false-positive rate on correct code, so a broken `ALT` operator
silently flatters the agent.
