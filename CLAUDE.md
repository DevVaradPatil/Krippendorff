# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A rubric-grounded grading agent for intro-Python assignments, built as an **evaluation project first and an agent second**. The full specification lives in [GRADING_AGENT_PROJECT.md](GRADING_AGENT_PROJECT.md) — read it before making design decisions; it contains the research framing, the six-week plan, and the reasoning behind the architecture.

The project's claim is *measured consistency and calibrated deferral against a known human-inconsistency baseline* (Krippendorff's α = 0.22, 1.79-band self-disagreement), not "agreement with human grades." Any change that improves human agreement while worsening self-consistency or `OK`/`ALT` false-positive rate is a regression.

Status: scaffolded, nothing implemented. Module stubs raise `NotImplementedError`.

## Commands

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows; use bin/activate on POSIX
pip install -e ".[dev]"
```

```bash
pytest                                  # all tests
pytest tests/test_metrics.py -k krippendorff -x   # single test
ruff check . && ruff format --check .   # lint + format
```

```bash
python -m eval.harness --config eval/configs/default.yaml   # the core loop
python -m eval.baselines --baseline test_only              # one baseline
python -m eval.adversarial --defenses on                   # C4 attack suite
python -m data.mutations.generate --out data/synthetic     # regenerate synthetic set
```

Entry points are declared in [pyproject.toml](pyproject.toml) and do not work yet — implement the module, then the command.

## Environment on this machine

- Python 3.12.3 at `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe` (spec says 3.11+; 3.12 is fine).
- **Docker is not installed.** S1 sandboxed execution cannot run here yet. Do not fall back to in-process `exec()` or `subprocess` on untrusted code to work around this — it is a hard rule (§11 of the spec). Implement against the Docker interface and skip/xfail those tests until Docker Desktop is available.
- No Ollama installed. Model calls will hit hosted free tiers; keep the cache on so reruns are free.
- Not a git repository yet.

## Architecture invariants

The pipeline is S0→S7 (diagram in spec §4). Each stage maps to one module:

| Stage | Module | Deterministic? |
|---|---|---|
| S0 static gate (AST, syntax, import allowlist) | [agent/static_gate.py](agent/static_gate.py) | yes |
| S1 sandboxed execution | [agent/sandbox.py](agent/sandbox.py) | yes |
| S2 style/complexity features | [agent/static_analysis.py](agent/static_analysis.py) | yes |
| S3 evidence bundle | [agent/evidence.py](agent/evidence.py) | yes |
| S4 LLM diagnosis | [agent/diagnose.py](agent/diagnose.py) | **no — the only LLM judgment call** |
| S5 score aggregation | [agent/aggregate.py](agent/aggregate.py) | yes |
| S6 confidence + routing | [agent/confidence.py](agent/confidence.py) | yes |
| S7 feedback + leak detection | [agent/feedback.py](agent/feedback.py) | LLM, constrained |

Rules that are load-bearing — violating any of them invalidates the evaluation:

1. **Correctness sub-scores never come from the LLM.** They are computed from S1 test results. Style sub-scores come from S2. Only design/documentation criteria reach S4. This is both the variance-reduction mechanism and the primary prompt-injection defense.
2. **Every LLM output is a Pydantic model**, retried on parse failure. No free-text parsing anywhere.
3. **Every diagnosis carries evidence line spans** into the student's source. A diagnosis without a valid span is a failed diagnosis, not a passing one — validate spans against the file rather than trusting the model.
4. **Comments and docstrings are stripped from the code before it reaches the LLM** and passed separately, explicitly framed as untrusted. This is where injections live.
5. **Ground-truth scores are derived by rule from the applied mutation**, never by asking a model or a human. Located in [data/mutations/](data/mutations/) alongside the operator that produced them.
6. **Feedback must not leak the reference solution** — [agent/feedback.py](agent/feedback.py) runs substring and n-gram overlap checks before returning.

## Shared contracts

[agent/schemas.py](agent/schemas.py) holds the Pydantic models and the misconception enum used by the agent, the data generators, and the eval harness. Changing a field there changes the on-disk format of `data/synthetic/` and every cached result. If you change it, bump `SCHEMA_VERSION` and say so — stale caches silently poison the metrics.

The 14-label misconception taxonomy (`OBO`, `CMP`, `ACC`, `DIV`, `MUT`, `ALI`, `SCP`, `REC`, `LOOP`, `CONV`, `EDGE`, `TYPE`, `OK`, `ALT`) is fixed by the spec. `OK` and `ALT` are correct submissions and must stay at ~20% of the set; they exist to measure the false-positive rate, which is the single most important number in C2.

Rubric criteria, weights and band descriptors live in [rubric/rubric.yaml](rubric/rubric.yaml). Code reads them; it does not hardcode weights.

## Working order

Build the eval before the agent. Week 1's deliverable is a harness that produces a **test-only baseline number** on 300 labeled submissions — every later claim is measured relative to it. A change to the agent with no eval run attached is not finished work.

Baselines in [eval/baselines.py](eval/baselines.py) are non-negotiable: test-only, zero-shot LLM, static-analysis-only, human (from Menagerie), full agent. If the full agent loses to test-only, that is a reportable finding, not a bug to hide.

## Conventions

- Providers (Gemini/Groq/OpenRouter/Ollama) are reached through one OpenAI-compatible client in [agent/llm.py](agent/llm.py); cross-model comparison is a deliverable, so never hardcode a model name outside config.
- Every model call is cached on a hash of (prompt, model, params, seed) so N=5 consistency runs and reruns are cheap; the consistency runs deliberately bypass the cache via a run index in the key.
- Results are append-only JSONL under `results/`; figures are regenerated from them, never edited by hand.
- The package directory `eval/` shadows the builtin `eval()` only when imported as a bare name — import submodules (`from eval import metrics`), don't `import eval`.
