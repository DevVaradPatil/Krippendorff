# Krippendorff

A rubric-grounded code-grading agent for intro-Python assignments, built to answer the question most grading demos skip: **how do you know it's any good, and what's the baseline?**

Named for Krippendorff's α — the inter-rater reliability statistic that makes this project's central point. Human graders score α ≈ 0.22 against each other on the same rubric; any grading agent evaluated without that number beside it is being graded against a standard nobody has checked.

The same research finds those graders also disagree with *themselves* — by 1.79 grade bands, on submissions they had already marked. So "agreement with human grades" is not a meaningful headline. Krippendorff measures **self-consistency**, **misconception-diagnosis F1**, **calibrated deferral**, and **prompt-injection resistance** instead — each against a stated baseline.

## Results

120 labelled synthetic submissions across 16 problems. Both LLM rows use `gemini-3.1-flash-lite` at temperature 0. Full detail and caveats in [results/REPORT.md](results/REPORT.md).

| System | Band accuracy | Self-agreement (bands) | Misconception macro-F1 | FP rate on correct code | Attack success | ₹/submission |
|---|---|---|---|---|---|---|
| Test-only baseline | 1.000 † | 0.00 | 0.100 | 0.000 | — | 0.00 |
| Static analysis only | 0.475 | 0.00 | 0.021 | 0.000 | — | 0.00 |
| Zero-shot LLM | 0.458 | 0.00 | 0.472 | **0.125** | **19%** | 0.010 |
| Human (literature) | — | **1.79** | — | — | — | — |
| **Full agent** | **0.892** | **0.00** | **0.932** | **0.000** | **1%** | 0.017 |

**The pipeline is worth roughly double the prompt.** Same model, same items, the only difference being the engineering: macro-F1 0.472 → **0.932**, and the false-positive rate on correct submissions 0.125 → **0.000**. A zero-shot grader flagged one in eight working submissions as buggy; the full agent flagged none of 24, identifying all 21 `OK` submissions with precision and recall of 1.00.

**Self-consistency: 0.00 bands across three independent passes, against a 1.79-band human baseline.** Measured at temperature 0, which is the deployment configuration — it says the system is reproducible, not that the model is free of uncertainty.

**Prompt injection: 19% success against a naive grader, 1% against this pipeline** (8 attack families × 10 submissions × 3 architectures, 240 attacked gradings each paired with a clean control). Of the 15 attacks that beat the naive grader, 10 both inflated the score *and* relabelled broken code as correct.

And the part that contradicts the design intent: **stripping comments before the model sees them (1%) and passing them inside an untrusted block (0%) are indistinguishable.** What earned the drop is structural — correctness is 60% of the rubric and comes from the test suite, so the model only controls the 15% design weight. The one attack that got through moved a score by 0.03 and left the diagnosis correct. Input isolation is worth keeping as defence in depth, but the architecture is the defense.

**† That 1.000 is a tautology, not a result.** Ground truth is derived by rule from the tests, and the test-only baseline reads the same tests, so it cannot miss — correctness is 60% of the rubric weight. Band accuracy is therefore not a discriminating metric on synthetic data for any system that runs the tests, which is why the full agent's 0.892 is *lower* than a baseline it beats on every metric that discriminates.

A zero false-positive rate is likewise cheap on its own: static-analysis-only scores 0.000 by labelling everything `OK`, at macro-F1 0.021. The two must always be read together.

Negative findings are reported here too. The largest open threat to the headline: the agent is shown the reference solution, and every mutant is a small edit to it, so diagnosis is partly a diff-reading task and macro-F1 should be expected to fall on real submissions.

![False-positive rate on correct submissions](results/figures/false_positive_rate.png)

![Risk–coverage curve](results/figures/risk_coverage.png)

Both regenerate from `results/runs.jsonl` with `python -m eval.figures`. The full agent's risk–coverage curve is flat, and that is a caveat rather than a win: it means confidence is not separating right answers from wrong ones, because the agent is nearly always right on synthetic data. Selective grading should earn its place on real submissions, not here.

## How it works

Deterministic tools do everything they possibly can; the model is used only where judgment is genuinely required.

```
Submission → S0 static gate → S1 sandboxed tests → S2 static features
           → S3 evidence bundle → S4 LLM diagnosis → S5 aggregation
           → S6 confidence & routing → S7 feedback
```

Correctness is scored from the test suite and never touches the model. Style is scored from ruff and radon and never touches the model. Only design reaches the LLM, which returns a structured diagnosis with mandatory line-number evidence, validated against the file — a citation to a line that does not exist is a failed diagnosis and a human deferral, not a grade.

The feedback stage is deliberately given *less* than the diagnosis stage: S4 sees the reference solution, S7 does not, because the only thing the reference could add to feedback is the answer. A leak detector then verifies that rather than trusting it. **0 leaks in 15 generated responses.**

That structure is also the strongest injection defense available: an instruction hidden in a comment cannot move the 60% of the score that comes from tests.

## Getting started

```bash
git clone https://github.com/DevVaradPatil/Krippendorff.git && cd Krippendorff
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env    # add at least one provider key
```

```bash
python -m data.mutations.generate --out data/synthetic
python -m eval.harness --config eval/configs/default.yaml
```

Sandboxed execution requires Docker with Linux containers; student code is never executed on the host.

## Repository

| Path | Contents |
|---|---|
| `agent/` | The S0–S7 pipeline, one module per stage |
| `eval/` | Harness, metrics, the five baselines, adversarial suite |
| `data/problems/` | 25 problem specs, reference solutions, test suites |
| `data/mutations/` | Labelled mutation operators; the synthetic-set generator |
| `rubric/rubric.yaml` | Criteria, weights, band descriptors |
| `results/REPORT.md` | The actual deliverable |

Full specification, research framing and six-week plan: [GRADING_AGENT_PROJECT.md](GRADING_AGENT_PROJECT.md).

## Ethics

Designed as triage and draft, never autonomous final grading — the routing layer exists so a human decides the hard cases. No real student data is used without institutional approval and anonymisation. The goal is not to replace an inconsistent process with an unaudited one, but to make consistency measurable; failure modes, including any bias against unconventional-but-correct solutions, are reported rather than hidden.

## References

Messer, Brown, Kölling & Shi (2025), *How Consistent Are Humans When Grading Programming Assignments?* (arXiv:2409.12967) — human baseline and the Menagerie dataset. Further references in the project spec.
