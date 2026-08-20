"""Read-only view over what the eval harness produced.

The UI never grades anything and never calls a model: it reads
``results/runs.jsonl``, the labelled dataset, and the problem definitions, and
joins them. Grading belongs to the pipeline, where it is measured; a dashboard
that quietly re-graded would be a second, unevaluated grader.

The one thing it does write is the reviewer's own decision, appended to
``results/human_decisions.jsonl``. That is the point of the routing layer -- a
human resolving the cases the agent declined -- and it is kept separate from the
agent's output so the two can never be confused.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from agent.aggregate import band_for, load_rubric
from agent.schemas import CORRECT_LABELS, Submission
from data.problems.loader import Problem, load_all

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
DECISIONS = RESULTS / "human_decisions.jsonl"

#: The model whose run the queue shows. Records carry their model, and mixing
#: two of them in one queue would make the evidence trail meaningless.
DEFAULT_MODEL = "gemini-3.1-flash-lite"


@dataclass
class ReviewItem:
    """One graded submission, joined with its ground truth and problem."""

    submission: Submission
    problem: Problem
    record: dict
    feedback: str | None = None

    @property
    def id(self) -> str:
        return self.submission.submission_id

    @property
    def score(self) -> dict:
        return self.record["score"]

    @property
    def diagnosis(self) -> dict | None:
        return self.record.get("diagnosis")

    @property
    def predicted_label(self) -> str | None:
        return (self.diagnosis or {}).get("label")

    @property
    def true_label(self) -> str | None:
        return self.submission.true_label.value if self.submission.true_label else None

    @property
    def true_band(self) -> str:
        return band_for(self.submission.true_score or 0.0, load_rubric())

    @property
    def deferred(self) -> bool:
        return self.record.get("route") == "human_review"

    @property
    def agrees_with_truth(self) -> bool | None:
        if self.predicted_label is None or self.true_label is None:
            return None
        return self.predicted_label == self.true_label

    @property
    def is_false_positive(self) -> bool:
        """Correct work graded as buggy -- the failure that harms students."""
        correct = {m.value for m in CORRECT_LABELS}
        return self.true_label in correct and self.predicted_label not in correct

    @property
    def evidence_span(self) -> tuple[int, int] | None:
        spans = (self.diagnosis or {}).get("evidence") or []
        if not spans:
            return None
        return spans[0]["start_line"], spans[0]["end_line"]


@dataclass
class Queue:
    items: list[ReviewItem] = field(default_factory=list)
    system: str = "full_agent"
    model: str = DEFAULT_MODEL

    @property
    def deferred(self) -> list[ReviewItem]:
        return [i for i in self.items if i.deferred]

    @property
    def auto_graded(self) -> list[ReviewItem]:
        return [i for i in self.items if not i.deferred]

    @property
    def false_positives(self) -> list[ReviewItem]:
        return [i for i in self.items if i.is_false_positive]


def load_runs(path: Path | None = None) -> dict[tuple[str, str], dict[str, dict]]:
    """Every record, keyed by (system, model) then submission id."""
    path = path or RESULTS / "runs.jsonl"
    out: dict[tuple[str, str], dict[str, dict]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            key = (record.get("system", "?"), record.get("model") or "deterministic")
            # Later lines win within one (system, model): the log is append-only,
            # so a rerun appends rather than replacing.
            out.setdefault(key, {})[record["submission_id"]] = record
    return out


def available_runs() -> list[tuple[str, str, int]]:
    return sorted(
        ((system, model, len(records)) for (system, model), records in load_runs().items()),
        key=lambda row: (-row[2], row[0]),
    )


def load_feedback() -> dict[str, str]:
    path = RESULTS / "feedback.json"
    if not path.exists():
        return {}
    return {
        record["submission_id"]: record["feedback"]
        for record in json.loads(path.read_text(encoding="utf-8"))
    }


def load_queue(system: str = "full_agent", model: str = DEFAULT_MODEL) -> Queue:
    from eval.harness import load_submissions

    records = load_runs().get((system, model), {})
    submissions = {s.submission_id: s for s in load_submissions()}
    problems = {p.id: p for p in load_all()}
    feedback = load_feedback()

    items = [
        ReviewItem(
            submission=submissions[sid],
            problem=problems[submissions[sid].problem_id],
            record=record,
            feedback=feedback.get(sid),
        )
        for sid, record in records.items()
        if sid in submissions
    ]
    items.sort(key=lambda i: (not i.deferred, i.id))
    return Queue(items=items, system=system, model=model)


def load_summary() -> dict:
    path = RESULTS / "summary.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_adversarial() -> dict:
    path = RESULTS / "adversarial.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def record_decision(item: ReviewItem, verdict: str, band: str, note: str) -> None:
    """Append the reviewer's decision. Never modifies the agent's own output."""
    DECISIONS.parent.mkdir(parents=True, exist_ok=True)
    with DECISIONS.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "submission_id": item.id,
                    "verdict": verdict,
                    "final_band": band,
                    "agent_band": item.score["band"],
                    "agent_label": item.predicted_label,
                    "note": note,
                    "decided_at": datetime.now(UTC).isoformat(),
                }
            )
            + "\n"
        )


def decisions() -> dict[str, dict]:
    if not DECISIONS.exists():
        return {}
    out: dict[str, dict] = {}
    with DECISIONS.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                out[record["submission_id"]] = record
    return out
