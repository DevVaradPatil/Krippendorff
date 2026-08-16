# Evaluation Report

**Run date:** 2026-08-16 · **Schema:** 0.1.0 · **Dataset:** `data/synthetic/submissions.jsonl`
**Model:** `gemini-3.1-flash-lite` @ temperature 0.0, `reasoning_effort: none`
**Status:** Weeks 1–3. S0–S6 measured on 120 labelled submissions. S7 feedback and
the C4 adversarial suite are not built.

Reproduce with:

```bash
python -m data.mutations.generate
python -m eval.harness --systems test_only static_only zero_shot_llm full_agent --n-samples 1
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

All four run on the same 120 items, the two LLM systems on the same model.

| System | Band acc | Band dist | Score err | Macro-F1 | FP on OK/ALT | Acc@70% | ECE | Deferred |
|---|---|---|---|---|---|---|---|---|
| Test-only | 1.000 † | 0.000 | 0.017 | 0.100 | 0.000 | 1.000 | 0.332 | 0 |
| Static-analysis only | 0.475 | 1.167 | 0.229 | 0.021 | 0.000 | 0.488 | 0.275 | 0 |
| Zero-shot LLM | 0.458 | 0.808 | 0.147 | 0.472 | **0.125** | 0.500 | 0.520 | 0 |
| **Full agent** | **0.892** | 0.108 | **0.020** | **0.932** | **0.000** | **0.917** | **0.107** | 15/120 |
| Human (Menagerie) | — | — | — | — | — | — | — | — |

† Tautological — see §3. Human reference: 1.79 bands of self-disagreement,
inter-rater α = 0.22 (Messer et al. 2025).

**The pipeline is worth roughly double the prompt.** Same model, same items:
macro-F1 goes 0.472 → **0.932**, and the false-positive rate on correct
submissions goes 0.125 → **0.000**. That is the project's central question
answered — the sandbox, the evidence isolation, and the deterministic split
account for the gap, because nothing else differs between those two rows.

The zero-shot row also shows *how* it fails, which matters more than the
aggregate: it mislabelled 12 of 29 `CMP` submissions as `EDGE`, and it graded
one in eight correct submissions as buggy. A grader that penalises 12.5% of
working student code is not deployable at any accuracy.

Cost, on the free tier: 120 submissions used 184,641 input and 13,295 output
tokens, about ₹2 at list price, with zero schema-validation retries and zero
rejected evidence spans across 240 calls.

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

Three independent passes over 60 submissions, 180 diagnosis calls in total:

| | Full agent | Human graders (Messer et al. 2025) |
|---|---|---|
| Exact band match across repeats | **1.000** | 1 of 22 graders |
| Mean self-disagreement | **0.00 bands** | **1.79 bands** |

These were real calls, not cache replays: `run_index` is part of the cache key,
and passes 2 and 3 took 307 s and 310 s against the rate limiter while pass 1
replayed in 0.5 s. The agent returned the identical label, span and band on
every one of 60 submissions, three times over.

**This is measured at temperature 0.0, which is the deployment configuration,
and the claim should always be stated with that attached.** It says the system
is reproducible, not that the model is free of uncertainty — a fair reading is
"the agent removes grader-side variance entirely at temperature 0", against a
human baseline where one grader re-marking the same submission moved it 1.79
bands on average. Measuring latent uncertainty needs a temperature sweep, which
is not done here.

Note also what this makes of the N-sample machinery: with a deterministic model,
`n_samples > 1` costs three times as much and can never disagree. The
disagreement signal only earns its keep at temperature > 0, and the main sweep
was therefore run at `n_samples=1`.

On the same 60 items the agent scored band accuracy 0.933, macro-F1 0.952,
false-positive rate 0.000, ECE 0.067, deferring 13.3%.

## 5. C2 — Diagnosis

Macro-F1 **0.932** for the full agent, against 0.472 zero-shot, 0.100 test-only
and 0.021 static-only. Per class, full agent:

| Label | P | R | F1 | n | | Label | P | R | F1 | n |
|---|---|---|---|---|---|---|---|---|---|---|
| ACC | 1.00 | 0.75 | 0.86 | 8 | | LOOP | 0.50 | 1.00 | 0.67 | 3 |
| ALI | 1.00 | 1.00 | 1.00 | 4 | | MUT | 1.00 | 1.00 | 1.00 | 3 |
| ALT | 1.00 | 1.00 | 1.00 | 3 | | OBO | 0.86 | 0.92 | 0.89 | 13 |
| CMP | 1.00 | 0.86 | 0.93 | 29 | | OK | 1.00 | 1.00 | 1.00 | 21 |
| CONV | 1.00 | 1.00 | 1.00 | 3 | | REC | 0.67 | 1.00 | 0.80 | 4 |
| DIV | 1.00 | 0.91 | 0.95 | 11 | | SCP | 1.00 | 1.00 | 1.00 | 4 |
| EDGE | 0.93 | 1.00 | 0.96 | 13 | | TYPE | 1.00 | 1.00 | 1.00 | 1 |

**The weak classes are the small ones, and that is a caveat, not a result.**
`LOOP` (0.67) and `REC` (0.80) have three and four examples; their precision is
dragged by two or three misroutes each, which at that support is noise. `TYPE`,
`CONV`, `MUT` and `ALT` score 1.00 on one to three items apiece and should not
be quoted at all. Only `CMP` (29), `OBO` (13), `EDGE` (13), `DIV` (11) and `OK`
(21) have enough support to mean much, and those five sit between 0.89 and 1.00.

The residual confusions are the plausible ones: `CMP → REC` and `CMP → LOOP`
twice each, `ACC → OBO` and `ACC → LOOP` once each. A wrong comparison operator
and a missing base case can produce identical symptoms — non-termination — and
the agent is choosing between them on evidence that genuinely underdetermines
the answer.

The `OK` column is the one to watch: **21/21 correct submissions identified as
correct, precision and recall both 1.00**, versus zero-shot's 0.75 F1 and 12.5%
false-positive rate on the same items.

## 6. C3 — Calibration

Full agent: accuracy at 70% coverage **0.917**, ECE **0.107**, deferring 15 of
120 (12.5%). Every deferral came from the band-edge rule; no submission was
deferred for low confidence or, with a single sample, for disagreement.

That last point is a limitation of this run rather than of the design. At
`n_samples=1` the disagreement signal cannot fire at all, so C3 here is measured
with one of routing's three inputs disabled. The `band_margin` was also
recalibrated mid-phase, from 0.05 to 0.02: at 0.05 the rule deferred 70% of the
set on its own, because with five bands it makes half the score range "near an
edge" and swamps the signals routing exists for.

ECE 0.332 for test-only is real and reflects deliberate under-confidence: its
confidence is `|2·pass_fraction − 1|`, so a submission failing half its tests
reports low confidence while still landing in the right band.

## 7. C4 — Robustness

Not measured. The structural defense exists and is tested offline
(`tests/test_evidence.py`): comments and docstrings never reach the model by
default, and correctness comes from test results, so no injected instruction can
move the 60% weight it carries. What is missing is the attack suite that turns
that into a number.

## 7a. Operational

| | Full agent | Zero-shot |
|---|---|---|
| Calls per submission | 1 | 1 |
| Mean tokens per submission | 1,636 | 953 |
| Cost per submission (list price) | ₹0.017 | ₹0.010 |
| Cost for the 120-item set | **₹2.05** | ₹1.19 |
| Schema retries / invalid spans | 0 / 0 | 0 / — |
| Wall clock, 120 items | 600 s | 602 s |

Wall clock is rate-limiter-bound, not model-bound: the free tier allows 15
requests/minute and the config paces at 12, so 120 submissions take ten minutes
regardless of how fast the model answers. The run cost nothing — it fits inside
the free tier — and ₹2.05 is what it would cost at list price.

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
7. **One model, one temperature, one sample.** Everything above is
   `gemini-3.1-flash-lite` at temperature 0 with `n_samples=1`. The cross-model
   frontier is unmeasured, and `gemini-3.5-flash-lite` is configured and has its
   own free quota, so that comparison is one command away.
8. **The agent has seen the reference solution.** S3 hands the model the correct
   implementation as trusted context, and every mutant is a small edit to it, so
   diagnosis is partly a diff-reading task. Real submissions do not resemble the
   reference that closely, and macro-F1 0.932 should be expected to fall on real
   data. This is the single biggest threat to the headline number.
9. **Free-tier quota is the binding constraint on this key.** The 2.5-series
   models allow 20 requests/day, the 3.x lite models 500/day at 15/minute.
   A full sweep plus its zero-shot control plus a three-pass consistency run is
   ~420 calls, which fits in one day only just, and only on a 3.x model.
