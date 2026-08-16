# Evaluation Report

**Run date:** 2026-08-16 · **Schema:** 0.1.0 · **Dataset:** `data/synthetic/submissions.jsonl`
**Status:** Week 1. Deterministic pipeline (S0-S2, S5) and eval harness complete; no LLM stage yet.

Reproduce with:

```bash
python -m data.mutations.generate && python -m eval.harness --n-runs 3
```

## 1. Setup

16 problems, 105 test cases, all references and alternatives passing. Mutation
operators are applied per *site*, so one problem yields several distinct mutants
per misconception.

| Generation outcome | Count |
|---|---|
| Mutants kept | 163 |
| Discarded as equivalent (passed the whole suite) | 10 |
| Discarded for failing the static gate | 0 |
| Discarded broken OK/ALT variants | 0 |
| Correct variants subsampled away to hold OK+ALT near 20% | 43 |
| **Final dataset** | **120** |

Label distribution (OK+ALT = 24, **20.0%**):

| CMP | OK | EDGE | OBO | DIV | ACC | REC | ALI | SCP | MUT | ALT | CONV | LOOP | TYPE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 29 | 21 | 13 | 13 | 11 | 8 | 4 | 4 | 4 | 3 | 3 | 3 | 3 | 1 |

Execution: Docker 29.7.2, `python:3.12-slim`, `--network none`, 256 MB, 1 CPU,
64 PIDs, 5 s per test case, no host mounts (files streamed in as a tar).

## 2. Baselines

| System | Band acc | Band dist | Score err | Macro-F1 | FP on OK/ALT | Acc@70% | ECE | Self-agree |
|---|---|---|---|---|---|---|---|---|
| Test-only | **1.000** | 0.000 | 0.017 | 0.100 | 0.000 | 1.000 | 0.332 | 1.000 |
| Static-analysis only | 0.475 | 1.167 | 0.229 | 0.021 | 0.000 | 0.488 | 0.275 | 1.000 |
| Zero-shot LLM | — | — | — | — | — | — | — | — |
| Human (Menagerie) | — | — | — | — | — | — | — | — |
| Full agent | — | — | — | — | — | — | — | — |

Human reference: 1.79 bands of self-disagreement, inter-rater α = 0.22
(Messer et al. 2025).

## 3. The headline number is a tautology, and that is the finding

**Test-only scores 1.000 band accuracy, and this measures nothing.**

Ground truth is derived by rule from the applied mutation — which means the
correctness component of the ground-truth score is computed from the sandbox
test results. The test-only baseline reads *the same* test results. Verified
directly: for **every submission in the set** the correctness input to the
baseline is identical to the correctness input to the ground truth. Correctness carries
60% of the rubric weight and the band ladder is 15 points wide, so any system
that runs the tests lands in the right band every time.

This is a property of the evaluation design, not a strength of the baseline, and
it invalidates band accuracy as a discriminating metric on synthetic data. It is
recorded here rather than quietly dropped because reporting 100% without this
paragraph would be the single most misleading number the project could publish.

The metrics that do discriminate:

- **Score error, split by label.** Test-only is off by 0.003 on buggy
  submissions but **0.072 on OK/ALT** — over 20× worse. That gap is exactly the
  style and documentation degradation that tests cannot see, and it is the
  first evidence that a tests-only grader systematically misprices
  correct-but-scruffy work.
- **Macro-F1 = 0.100.** Tests can say *that* a submission failed, never *which*
  misconception caused it. This is the number the agent has to beat, and it is
  the whole educational case for the project.

**A zero false-positive rate can be bought by refusing to diagnose.** Both
baselines score 0.000 on OK/ALT: test-only because correct code passes its
tests, static-only because it labels everything `OK`. Static-only pairs that
perfect score with a macro-F1 of 0.021. The false-positive rate is only
meaningful read alongside F1, and future results must report them together.

## 4. C1 — Consistency

Both baselines are deterministic: exact-match self-agreement 1.000 over N=3, 0.0
bands of self-disagreement, against the human baseline of 1.79 bands. This is
the trivial case and is reported as a floor, not a result — it confirms the
pipeline contributes no variance of its own, so any disagreement measured once
S4 exists is attributable to the LLM.

## 5. C2 — Diagnosis

Macro-F1 0.100 (test-only), 0.021 (static-only). No confusion matrix worth
printing yet: test-only has exactly two predictions available to it, `OK` when
everything passes and the majority class otherwise.

## 6. C3 — Calibration

Accuracy at 70% coverage is 1.000 for test-only, inheriting the tautology in §3.
ECE 0.332 is real and reflects deliberate under-confidence: the baseline's
confidence is `|2·pass_fraction − 1|`, so a submission failing half its tests
reports low confidence while still landing in the right band.

## 7. C4 — Robustness

Not started. The structural defense already exists, though: correctness is
computed from test results, so no injected instruction can move the 60% weight
it carries.

## 8. Limitations

1. **The set is 120 submissions, against a target of 300.** Yield is ~10 kept
   mutants per problem, so the target needs roughly 24 problems; there are 16.
   Nothing else has to change — adding problems is mechanical.
2. **TYPE has a single example**, and MUT/LOOP/ALT/CONV have three each.
   Macro-F1 over classes that thin is high-variance, and the per-class numbers
   should not be quoted until each class has ~10 examples. The scarce codes are
   scarce for a structural reason: `TYPE` needs an explicit numeric conversion
   and `CONV` needs an iterative solver, and few intro problems have either.
3. **Design scores carry no signal.** Every ground-truth design sub-score is
   1.0, because a wrong loop bound is an implementation defect, not a design
   one. The 15% design weight is therefore untested by this dataset, which
   matters because design is exactly the criterion S4 will own.
4. **Band accuracy is not usable on synthetic data** for any system that runs
   the tests (§3). Real data with independent human grades — Menagerie — is the
   only way to test banding honestly.
5. **Latency figures are meaningless here.** Sandbox results are cached from
   generation, so the baseline "graded" 116 submissions in under 0.1 s. Cold
   figures need a cache-cleared run.
6. **Synthetic mutants are clean.** The realism layer (LLM rewriting in a
   struggling-student voice) is not built, so the gap to real submissions is
   unmeasured.
