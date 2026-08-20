"""The UI's data layer.

The console is read-only over the harness's output, and these tests pin the two
properties that makes it honest: it never re-derives a grade, and a reviewer's
decision is written somewhere the agent's own records are not.
"""

from __future__ import annotations

import json

import pytest

from agent.schemas import Misconception
from app import store

pytestmark = pytest.mark.skipif(
    not (store.RESULTS / "runs.jsonl").exists(), reason="no runs.jsonl yet"
)


@pytest.fixture(scope="module")
def queue():
    return store.load_queue()


def test_the_queue_joins_records_to_ground_truth(queue):
    assert queue.items
    item = queue.items[0]
    assert item.submission.submission_id == item.id
    assert item.problem.id == item.submission.problem_id


def test_scores_are_read_not_recomputed(queue):
    # The console must never re-derive a grade: a dashboard that quietly
    # regraded would be a second, unevaluated grader.
    for item in queue.items[:20]:
        assert item.score == item.record["score"]


def test_deferred_items_carry_a_reason(queue):
    for item in queue.deferred:
        assert item.record.get("route_reason"), f"{item.id} deferred without a reason"


def test_false_positives_are_correct_work_labelled_buggy(queue):
    correct = {m.value for m in (Misconception.OK, Misconception.ALT)}
    for item in queue.false_positives:
        assert item.true_label in correct
        assert item.predicted_label not in correct


def test_every_evidence_span_lies_inside_its_submission(queue):
    # The highlight the console draws must be a span that was validated upstream;
    # a span past the end of the file would silently render nothing.
    for item in queue.items:
        span = item.evidence_span
        if span is None:
            continue
        lines = len(item.submission.source.splitlines())
        assert 1 <= span[0] <= lines, f"{item.id} span starts at {span[0]} of {lines}"
        assert span[0] <= span[1] <= lines, f"{item.id} span ends at {span[1]} of {lines}"


def test_deferred_and_auto_partition_the_queue(queue):
    assert len(queue.deferred) + len(queue.auto_graded) == len(queue.items)


def test_runs_are_listed_per_model(queue):
    runs = store.available_runs()
    assert runs
    models = {model for _, model, _ in runs}
    # Two models were graded as full_agent; keeping them apart is what stops the
    # console showing one model's records under another's name.
    assert len(models) > 1


def test_a_decision_is_written_beside_the_agent_output_not_into_it(queue, monkeypatch, tmp_path):
    path = tmp_path / "human_decisions.jsonl"
    monkeypatch.setattr(store, "DECISIONS", path)
    item = queue.items[0]
    before = dict(item.record)

    store.record_decision(item, "override", "C", "checked by hand")

    written = json.loads(path.read_text(encoding="utf-8").strip())
    assert written["submission_id"] == item.id
    assert written["verdict"] == "override"
    assert written["final_band"] == "C"
    assert written["agent_band"] == before["score"]["band"]
    # The agent's own record is untouched, so recomputing metrics later cannot
    # accidentally read a human's decision as the agent's output.
    assert item.record == before
