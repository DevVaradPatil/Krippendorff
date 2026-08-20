# Review console

The human-review queue: a Streamlit app over what the eval harness produced.

```bash
pip install -e ".[ui]"
streamlit run app/review.py
```

## What it is

**Triage, not grading.** The agent has already graded and already decided what it
was unsure of. This is where a person resolves those cases — which is the entire
justification for the routing layer, and the reason the project can claim to be
deployable at all.

Four views:

| View | Purpose |
|---|---|
| **Review queue** | Only what the agent deferred. Each card shows the submission with the cited evidence lines highlighted, the score split by stage, the routing reason, and a form to record a decision. |
| **All submissions** | Everything graded, filterable by ground-truth label, by disagreement with ground truth, and by false positives on correct work. |
| **Results** | The headline table, the figures, and the injection-resistance arms. |
| **About** | What the console is, and the known limits from `results/REPORT.md`. |

## Three properties it keeps

**It never grades.** No model is called and no score is recomputed;
`app/store.py` reads `results/runs.jsonl` and joins it to the dataset. A
dashboard that quietly re-derived a grade would be a second, unevaluated grader.

**It shows where each number came from.** Every card breaks the score into
correctness (S1, the test suite), style (S2, ruff and radon) and design (S4, the
model). That split is the architectural argument, and the bars make it visible
rather than asserted: the model owns one of the three, weighted 15%.

**Reviewer decisions stay separate.** They append to
`results/human_decisions.jsonl` and never touch the agent's records, so
recomputing metrics later cannot mistake a human's override for the agent's
output.

## Selecting a run

The sidebar lists every `(system, model)` pair present in the log. Two models
were graded as `full_agent`, so the pair is the key — showing one model's records
under another's name would make the whole evidence trail wrong.
