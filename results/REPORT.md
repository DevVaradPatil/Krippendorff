# Evaluation Report

Status: no runs yet. Sections below are the required shape of the deliverable;
fill each one from harness output, and record the run id and config hash beside
every number so it can be reproduced.

## 1. Setup

- Dataset: size, problem count, label distribution, OK/ALT fraction
- Models compared, with the config each ran under
- Hardware, sandbox limits, date, cache state

## 2. Baselines

Table of all five systems on every headline metric. Test-only comes first
because it is the bar the agent has to clear.

## 3. C1 — Consistency

Self-agreement over N=5 reruns: exact-match rate and mean absolute band
distance, reported next to the 1.79-band human self-disagreement baseline. On
Menagerie, agent-vs-human α reported beside human-vs-human α computed on the
same items.

## 4. C2 — Diagnosis

Macro-F1 over the 14-class taxonomy, the confusion matrix, and which
misconceptions get conflated. Then the number that matters most: the
false-positive rate on `OK` and `ALT`.

## 5. C3 — Calibration

Risk–coverage curve, expected calibration error, and the headline framing:
*at 70% coverage, band accuracy is X%*.

## 6. C4 — Robustness

Attack success rate per injection family, with defenses off and on, plus which
defense accounts for which portion of the drop.

## 7. Cross-model frontier

Cost, accuracy and consistency for each model. The question being answered is
whether the expensive model is worth it.

## 8. Negative findings and limitations

Anything that did not work, the synthetic-to-real transfer gap, and where the
evaluation itself is weak. This section is not optional.
