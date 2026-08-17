"""S0 -> S7 orchestration.

Plain Python by design. A framework goes in when the state genuinely needs one;
right now the pipeline is a straight line with two early exits (gate failure,
diagnosis failure) and one fan-out (N diagnosis samples).

Note where the score comes from at each step: correctness from S1, style and
documentation from S2, design from S4. The model contributes one number out of
four, weighted 15%, and cannot touch the other three.
"""

from __future__ import annotations

import time

from agent import diagnose as s4
from agent import evidence as s3
from agent import feedback as s7
from agent import static_analysis as s2
from agent import static_gate as s0
from agent.aggregate import aggregate, load_rubric
from agent.confidence import RoutingPolicy, consensus, route
from agent.llm import ModelConfig
from agent.sandbox import SandboxLimits, run_tests
from agent.schemas import Diagnosis, GradingResult, Route, Score, Span, Submission
from data.problems.loader import Problem


def grade(
    submission: Submission,
    problem: Problem,
    config: ModelConfig,
    *,
    policy: RoutingPolicy | None = None,
    include_comments: bool = False,
    limits: SandboxLimits | None = None,
    use_cache: bool = True,
    run_offset: int = 0,
    write_feedback: bool = False,
) -> GradingResult:
    """Run one submission through the full pipeline."""
    policy = policy or RoutingPolicy()
    rubric = load_rubric()
    started = time.monotonic()

    gate = s0.check(submission.source)
    if not gate.passed:
        return _gate_failure(submission, gate, rubric, started)

    results = run_tests(submission.source, problem.tests_path, limits)
    features = s2.extract(submission.source)
    bundle = s3.build(
        problem_id=problem.id,
        problem_statement=problem.statement,
        reference_solution=problem.reference,
        source=submission.source,
        results=results,
        features=features,
        include_comments=include_comments,
    )

    samples: list[Diagnosis] = []
    failures: list[str] = []
    tokens_in = tokens_out = 0
    cost = 0.0
    for sample in range(policy.n_samples):
        # Offset by the outer repeat so a second pass over the dataset draws
        # fresh completions rather than replaying this one's cache.
        run_index = run_offset * policy.n_samples + sample
        try:
            diagnosis, completion = s4.diagnose(
                bundle, config, run_index=run_index, use_cache=use_cache
            )
        except s4.DiagnosisFailure as exc:
            failures.append(str(exc)[:200])
            continue
        samples.append(diagnosis)
        tokens_in += completion.tokens_in
        tokens_out += completion.tokens_out
        cost += completion.cost_inr(config)

    # Design is the only sub-score the model owns. With no usable sample there
    # is nothing to grade on, so the submission goes to a human rather than
    # receiving a made-up number.
    agreed = consensus(samples) if samples else None
    design = agreed.subjective_scores.get("design", 1.0) if agreed else 1.0
    score = aggregate(results, features, design=design, rubric=rubric)
    destination, reason = route(samples, score, flags=[], policy=policy)

    # S7 costs another call per submission and never changes the grade, so it is
    # opt-in: the eval runs that produce C1-C3 do not need it.
    feedback = None
    if write_feedback and agreed is not None:
        feedback, used_template, completion = s7.generate(
            agreed,
            submission.source,
            results,
            problem.statement,
            problem.reference,
            config,
            run_index=run_offset,
            use_cache=use_cache,
        )
        if completion is not None:
            tokens_in += completion.tokens_in
            tokens_out += completion.tokens_out
            cost += completion.cost_inr(config)
        if used_template:
            failures.append("feedback fell back to template")

    return GradingResult(
        submission_id=submission.submission_id,
        score=score,
        diagnosis=agreed,
        route=destination,
        route_reason=reason if not failures else f"{reason}; {failures[0]}",
        feedback=feedback,
        consistency_samples=[s.label.value for s in samples],
        model=config.name,
        tokens=tokens_in + tokens_out,
        cost_inr=round(cost, 6),
        latency_s=round(time.monotonic() - started, 3),
    )


def _gate_failure(submission, gate, rubric, started) -> GradingResult:
    """S0 rejection: structured, scored zero on correctness, never sent to a model."""
    problems = gate.disallowed_imports + gate.banned_constructs
    detail = gate.syntax_error or ", ".join(problems)
    return GradingResult(
        submission_id=submission.submission_id,
        score=Score(
            correctness=0.0,
            style=0.0,
            design=0.0,
            total=0.0,
            band=rubric["bands"][-1]["name"],
        ),
        diagnosis=Diagnosis(
            label="EDGE" if gate.syntax_error else "TYPE",
            evidence=[Span(start_line=1, end_line=1)],
            rationale=f"did not compile or violated the import policy: {detail}",
            confidence=1.0,
        )
        if gate.syntax_error
        else None,
        route=Route.HUMAN_REVIEW,
        route_reason=f"static gate: {detail}",
        latency_s=round(time.monotonic() - started, 3),
    )
