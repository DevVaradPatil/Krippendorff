# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**Krippendorff** — a rubric-grounded grading agent for intro-Python assignments, built as an **evaluation project first and an agent second**. Named for Krippendorff's α, the inter-rater reliability statistic the project's central claim is measured with. Repo: https://github.com/DevVaradPatil/Krippendorff

The full specification lives in [GRADING_AGENT_PROJECT.md](GRADING_AGENT_PROJECT.md) — read it before making design decisions; it contains the research framing, the six-week plan, and the reasoning behind the architecture.

The project's claim is *measured consistency and calibrated deferral against a known human-inconsistency baseline* (Krippendorff's α = 0.22, 1.79-band self-disagreement), not "agreement with human grades." Any change that improves human agreement while worsening self-consistency or `OK`/`ALT` false-positive rate is a regression.

Status: **C1–C4 measured, S0–S7 complete.** Full agent: macro-F1 **0.932**, false-positive rate on correct code **0.000**, self-disagreement **0.00 bands** vs the human 1.79, injection attack success **1%** vs 19% for a naive grader. Zero-shot on the same model and items: 0.472 macro-F1 and 0.125 FP — the pipeline is the difference. S7 ships feedback with 0/15 solution leaks. The cross-model frontier and the Menagerie human baseline are unmeasured.

Read [results/REPORT.md](results/REPORT.md) before trusting any number. Two things to carry into any change: the test-only band accuracy of 1.000 is a **tautology** (ground truth is rule-derived from the same tests the baseline reads, so band accuracy does not discriminate on synthetic data), and the agent is shown the reference solution while every mutant is a small edit to it — so diagnosis is partly diff-reading and 0.932 should be expected to fall on real submissions.

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
python -m data.mutations.generate            # regenerate the labelled set (~2 min cold)
python -m eval.harness --n-runs 3            # the core loop; --limit N for a quick pass
python -m eval.harness --preview             # print the exact S4 prompt, no model call
python -m eval.harness --systems full_agent --model primary --limit 20
python -m eval.baselines --baseline test_only
python -m eval.adversarial --defenses on     # C4 suite: not implemented yet
```

`--model` selects a key under `models:` in [eval/configs/default.yaml](eval/configs/default.yaml);
`primary` is Gemini Flash. Model names, prices and rate limits live there and
nowhere else — the cross-model frontier is a deliverable, so a model swap must
never require a code change.

Docker Desktop must be running before either of the first two — they execute every
submission in a container. `agent.sandbox.available()` reports whether the daemon
is reachable; tests marked `docker` skip when it is not.

Sandbox results are cached under `.cache/sandbox/` keyed on (source, tests,
runner, image, limits), so generation and the baseline each execute a given
submission once. That makes reruns nearly free and makes the harness's latency
numbers meaningless on a warm cache — clear it before quoting timings.

## Environment on this machine

- Python 3.12.3 at `C:\Users\User\AppData\Local\Programs\Python\Python312\python.exe` (spec says 3.11+; 3.12 is fine).
- **Docker Desktop 29.7.2**, WSL2 backend, Linux containers. Verified working with the exact sandbox flags S1 needs: `docker run --rm --network none --memory 256m --cpus 1 --pids-limit 64 python:3.12-slim` runs and the image is pulled locally. The `--pids-limit` flag is `pids_limit` in the Python SDK's `containers.run`.
- Docker Desktop is installed **per-user**, not in `Program Files`: `C:\Users\User\AppData\Local\Programs\DockerDesktop\resources\bin`. That directory is on the machine PATH, but a shell started before the install won't see it — if `docker` is "not recognized", the shell is stale, not the install. The `docker-credential-desktop` helper lives in the same directory, so a partial PATH breaks image *pulls* while `docker info` still works.
- The `docker` CLI is **not** available inside WSL Ubuntu (Docker Desktop's WSL integration for that distro is off). This doesn't matter — the Python SDK talks to the Windows daemon over the named pipe. Don't add a WSL execution path.
- **`docker.from_env()` does not work here.** It assumes `\\.\pipe\docker_engine`, but Docker Desktop's default context (`desktop-linux`) listens on `dockerDesktopLinuxEngine`, so the SDK reports "cannot find the file specified" while the CLI works fine. [agent/sandbox.py](agent/sandbox.py) tries `DOCKER_HOST` and then the known endpoints in order; use `_client()` rather than constructing a client yourself.
- Docker Desktop **stops when the machine idles**, and the daemon is then unreachable until the app is relaunched. If the sandbox raises `SandboxUnavailableError`, check the app is running before debugging anything else.
- **Gemini free-tier quota is per-model and differs by generation.** Measured 2026-08-16: the 2.5 models allow **20 requests/day** (unusable for a sweep), the 3.x lite models **500/day at 15/minute**. `gemini-2.0-flash` is gone (404). Use `primary` (`gemini-3.1-flash-lite`) or `flash35` (`gemini-3.5-flash-lite`); each has its own 500, which is what makes the cross-model comparison affordable. `python eval/probe_quota.py` re-checks for one call per provider.
- `gemini-3.5-flash-lite` **rejects `reasoning_effort: none`** with a 400; it accepts `low`. `gemini-3.1-flash-lite` accepts `none`. Leaving reasoning on spends the `max_tokens` budget on thinking and can return empty content.
- The `GROQ_API_KEY` and `OPENROUTER_API_KEY` currently in `.env` both return 401.
- A 429 is not necessarily fatal: `agent/llm.py` distinguishes a per-minute throttle (retry) from a daily cap (stop) on the quota **id**, not the metric name — both report the same `..._free_tier_requests` metric, and confusing them once burned ten minutes of backoff and once aborted a healthy run. `tests/test_quota.py` pins it with the real response bodies.
- LLM responses are cached under `.cache/llm/` on (prompt, model, params, **run_index**). The run index is what makes N-sample consistency runs reach the API instead of replaying one cached answer — removing it would report perfect self-agreement for free.
- Git repo on `main`, remote `origin` → https://github.com/DevVaradPatil/Krippendorff.git. The local directory is still named `grading_agent`; that's cosmetic.

Untrusted code still never runs in-process or on the host, Docker present or not — no `exec()`, no bare `subprocess`. That rule doesn't relax now that the sandbox works (spec §11).

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

S7 is opt-in (`write_feedback=True`): it costs a call per submission and never changes a grade, so the C1–C3 runs skip it. Measure it with `python -m eval.feedback_run --n 15`.

Rules that are load-bearing — violating any of them invalidates the evaluation:

1. **Correctness sub-scores never come from the LLM.** They are computed from S1 test results. Style sub-scores come from S2. Only design/documentation criteria reach S4. This is both the variance-reduction mechanism and the primary prompt-injection defense.
2. **Every LLM output is a Pydantic model**, retried on parse failure. No free-text parsing anywhere.
3. **Every diagnosis carries evidence line spans** into the student's source. A diagnosis without a valid span is a failed diagnosis, not a passing one — validate spans against the file rather than trusting the model.
4. **Comments and docstrings are stripped from the code before it reaches the LLM** and passed separately, explicitly framed as untrusted. This is where injections live.
5. **Ground-truth scores are derived by rule from the applied mutation**, never by asking a model or a human. Located in [data/mutations/](data/mutations/) alongside the operator that produced them.
6. **Feedback must not leak the reference solution.** The primary mechanism is that **S7 is never given the reference** — only S4 gets it. [agent/feedback.py](agent/feedback.py) then verifies with a verbatim-line check and an n-gram check, both of which subtract the student's own code first (quoting their line back is the point of feedback, not a leak). The n-gram ratio is normalised **over the reference**, not over the feedback: the other direction is diluted by prose and measured 0.117 for a solution pasted whole, under its own 0.15 threshold, so it could never fire.

## Shared contracts

[agent/schemas.py](agent/schemas.py) holds the Pydantic models and the misconception enum used by the agent, the data generators, and the eval harness. Changing a field there changes the on-disk format of `data/synthetic/` and every cached result. If you change it, bump `SCHEMA_VERSION` and say so — stale caches silently poison the metrics.

The 14-label misconception taxonomy (`OBO`, `CMP`, `ACC`, `DIV`, `MUT`, `ALI`, `SCP`, `REC`, `LOOP`, `CONV`, `EDGE`, `TYPE`, `OK`, `ALT`) is fixed by the spec. `OK` and `ALT` are correct submissions and must stay at ~20% of the set; they exist to measure the false-positive rate, which is the single most important number in C2.

Rubric criteria, weights and band descriptors live in [rubric/rubric.yaml](rubric/rubric.yaml). Code reads them; it does not hardcode weights.

## Ground truth and the mutation generator

[data/mutations/operators.py](data/mutations/operators.py) finds mutation sites on the AST but splices replacement **text** over the node's source span. Never switch it to `ast.unparse` — that discards every comment in the file, which would silently zero the documentation criterion and make the `OK` operator's comment-stripping a no-op.

Two filters in [data/mutations/generate.py](data/mutations/generate.py) keep labels honest, and both must survive any refactor:

- A mutant that **passes the whole suite is discarded as equivalent**, not labelled. 10 of 173 were dropped this way.
- An `OK`/`ALT` variant that **fails any test is discarded**, because a supposedly-correct sample that is actually broken corrupts the false-positive rate.

`tests/test_operators.py` asserts that every label a problem declares in `misconceptions_applicable` has an operator that actually matches it — a declared-but-unmatchable label silently under-fills that class.

## Working order

Build the eval before the agent. Week 1's deliverable — a harness producing a test-only baseline number — is **done**; every later claim is measured relative to it. A change to the agent with no eval run attached is not finished work.

Next: run the LLM systems. `.env` needs `GEMINI_API_KEY` from https://aistudio.google.com/apikey; nothing else blocks a measurement. The dataset is 120 submissions against the spec's target of 300; yield is ~10 per problem, so ~8 more problems closes it (use the `add-problem` skill).

`tests/test_pipeline.py` stubs the model and asserts the split holds in the real wiring: swinging the design sub-score from 1.0 to 0.0 moves the total by exactly 0.15, the design weight, and no more. If that assertion ever fails, the LLM has leaked into a criterion it does not own.

Baselines in [eval/baselines.py](eval/baselines.py) are non-negotiable: test-only, zero-shot LLM, static-analysis-only, human (from Menagerie), full agent. If the full agent loses to test-only, that is a reportable finding, not a bug to hide.

## The C4 suite

[eval/adversarial.py](eval/adversarial.py) compares three *architectures* rather than toggling a flag: `naive` (zero-shot, raw code), `quarantine` (pipeline, comments shown inside an untrusted block), `stripped` (pipeline as shipped). Every attacked grading is paired with a clean control of the same submission on the same model — without it, "attack success" measures nothing.

Measured result: comment stripping and comment quarantining are **indistinguishable** (1% vs 0%). The drop from 19% comes from correctness being computed from tests, which caps what any injection can move at the 15% design weight. Don't add input-sanitising defenses and claim credit for the structural one.

Run it per-arm (`--arms naive`), not all three at once: each arm is ~90 calls and about eight minutes at the free tier's pacing.

## Conventions

- Providers (Gemini/Groq/OpenRouter/Ollama) are reached through one OpenAI-compatible client in [agent/llm.py](agent/llm.py); cross-model comparison is a deliverable, so never hardcode a model name outside config.
- Every model call is cached on a hash of (prompt, model, params, seed) so N=5 consistency runs and reruns are cheap; the consistency runs deliberately bypass the cache via a run index in the key.
- Results are append-only JSONL under `results/`; figures are regenerated from them with `python -m eval.figures`, never edited by hand. That loader keys records on **(system, model, run_index)** — two models graded as `full_agent` at run 0, and without the model in the key the later sweep silently replaces the earlier one and every figure shows a different model than its caption claims.
- The package directory `eval/` shadows the builtin `eval()` only when imported as a bare name — import submodules (`from eval import metrics`), don't `import eval`.
