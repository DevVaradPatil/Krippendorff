---
name: run-eval
description: Run the evaluation harness or a baseline and record the result properly. Use when measuring a change, producing numbers for REPORT.md, or comparing models.
---

# Run the eval

A change to the agent with no eval run attached is not finished work.

## Before running

- Check whether `SCHEMA_VERSION` in `agent/schemas.py` changed since the cached
  results were written. If it did, clear `.cache/` — stale cached completions
  under a new schema silently poison the metrics.
- Note the config hash and git revision. Every number in `results/REPORT.md`
  must be traceable to both.

## Commands

```bash
python -m eval.harness --config eval/configs/default.yaml
```

```bash
python -m eval.baselines --baseline test_only
```

```bash
python -m eval.adversarial --defenses on
```

For iteration, run against a subset with `n_runs: 1` and a local model. Save the
N=5 runs and the hosted models for a result you intend to report — free-tier
limits change often and a blocked run halfway through a batch wastes the whole
sweep.

## Reading the output

Always report a baseline beside the agent. Specifically:

- **Never report agent-vs-human agreement alone.** It goes next to
  human-vs-human α (0.22 from the literature, or computed on Menagerie), or it
  is not reported.
- **Self-consistency goes next to 1.79 bands**, the human self-disagreement
  baseline.
- **Check the false-positive rate on `OK`/`ALT` on every run**, not just when
  reporting. It is the number that most easily regresses unnoticed, and it is
  the failure mode that actually harms students.
- **Test-only is the bar.** If the full agent does not clear it on C2 and C3,
  that is a finding to write up, not a bug to fix by tuning until it passes.

## After running

Append to the JSONL under `results/`, regenerate figures from it rather than
editing anything by hand, and update the relevant section of
`results/REPORT.md` with the run id, config hash, and date beside the number.
