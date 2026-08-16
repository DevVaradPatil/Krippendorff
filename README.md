# Krippendorff

A rubric-grounded code-grading agent for intro-Python assignments, built to answer the question most grading demos skip: **how do you know it's any good, and what's the baseline?**

Named for Krippendorff's α — the inter-rater reliability statistic that makes this project's central point. Human graders score α ≈ 0.22 against each other on the same rubric; any grading agent evaluated without that number beside it is being graded against a standard nobody has checked.

The same research finds those graders also disagree with *themselves* — by 1.79 grade bands, on submissions they had already marked. So "agreement with human grades" is not a meaningful headline. Krippendorff measures **self-consistency**, **misconception-diagnosis F1**, **calibrated deferral**, and **prompt-injection resistance** instead — each against a stated baseline.

## Results

Week 1: deterministic pipeline and eval harness, on 120 labelled synthetic submissions across 16 problems. No LLM stage yet, so the rows that need one are empty. Full detail and caveats in [results/REPORT.md](results/REPORT.md).

| System | Band accuracy | Self-agreement (bands) | Misconception macro-F1 | FP rate on correct code | Attack success | ₹/submission |
|---|---|---|---|---|---|---|
| Test-only baseline | 1.000 † | 0.00 | 0.100 | 0.000 | — | 0.00 |
| Static analysis only | 0.475 | 0.00 | 0.021 | 0.000 | — | 0.00 |
| Zero-shot LLM | — | — | — | — | — | — |
| Human (literature) | — | 1.79 | — | — | — | — |
| **Full agent** | — | — | — | — | — | — |

**† That 1.000 is a tautology, not a result.** Ground truth is derived by rule from the tests, and the test-only baseline reads the same tests, so it cannot miss — correctness is 60% of the rubric weight. Band accuracy is therefore not a discriminating metric on synthetic data, for any system that runs the tests. The numbers that do discriminate are macro-F1 (0.100: tests say *that* a submission failed, never *which* misconception caused it) and the score error split by label (0.003 on buggy code, 0.072 on correct-but-scruffy code — the first evidence that a tests-only grader systematically misprices good work in bad clothing).

A zero false-positive rate is likewise cheap: static-analysis-only scores 0.000 by labelling everything `OK`, at a macro-F1 of 0.021. The two must always be read together.

Negative findings are reported here too. If the full agent does not beat the test-only baseline, that appears in this table.

## How it works

Deterministic tools do everything they possibly can; the model is used only where judgment is genuinely required.

```
Submission → S0 static gate → S1 sandboxed tests → S2 static features
           → S3 evidence bundle → S4 LLM diagnosis → S5 aggregation
           → S6 confidence & routing → S7 feedback
```

Correctness is scored from the test suite and never touches the model. Style is scored from ruff and radon and never touches the model. Only design and documentation reach the LLM, which returns a structured diagnosis with mandatory line-number evidence. Three samples per submission give a disagreement measure, which both quantifies consistency and decides what gets routed to a human.

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
