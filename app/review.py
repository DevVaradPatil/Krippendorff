"""Krippendorff review console.

A triage queue, not a grading tool. The agent has already graded; this shows what
it decided, what evidence it cited, and -- for the cases it declined -- lets a
human resolve them. Nothing here calls a model or changes a score.

Run with:
    streamlit run app/review.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import store  # noqa: E402

st.set_page_config(page_title="Krippendorff review console", page_icon="📐", layout="wide")

BAND_COLOURS = {"A": "#1f7a4d", "B": "#3d7a1f", "C": "#8a6d1f", "D": "#a35520", "E": "#993333"}

CSS = """
<style>
  .kr-band {display:inline-block; padding:2px 10px; border-radius:4px; color:#fff;
            font-weight:600; font-size:0.95rem;}
  .kr-chip {display:inline-block; padding:2px 8px; border-radius:4px; background:#eef1f5;
            font-family:ui-monospace,monospace; font-size:0.82rem; margin-right:6px;}
  .kr-muted {color:#666; font-size:0.86rem;}
  .kr-code {font-family:ui-monospace,monospace; font-size:0.83rem; line-height:1.45;
            white-space:pre; overflow-x:auto; border:1px solid #e6e6e6; border-radius:6px;
            padding:10px 0; background:#fcfcfc;}
  .kr-line {padding:0 12px;}
  .kr-hit {background:#fff3bf; border-left:3px solid #e0a800; padding-left:9px;}
  .kr-num {color:#aaa; user-select:none;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def band_pill(band: str) -> str:
    colour = BAND_COLOURS.get(band, "#666")
    return f'<span class="kr-band" style="background:{colour}">{band}</span>'


def code_with_span(source: str, span: tuple[int, int] | None) -> str:
    """Render the submission with the cited evidence lines highlighted.

    The highlight is the point of the evidence contract: a diagnosis that cannot
    point at real lines is rejected upstream, so any span shown here was
    validated against this exact file.
    """
    rows = []
    for number, line in enumerate(source.splitlines(), start=1):
        hit = span is not None and span[0] <= number <= span[1]
        css = "kr-line kr-hit" if hit else "kr-line"
        safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows.append(f'<div class="{css}"><span class="kr-num">{number:3d}</span>  {safe}</div>')
    return '<div class="kr-code">' + "".join(rows) + "</div>"


@st.cache_data(show_spinner=False)
def cached_queue(system: str, model: str):
    return store.load_queue(system, model)


def sidebar() -> tuple[str, str, str]:
    st.sidebar.title("Krippendorff")
    st.sidebar.caption("Rubric-grounded grading agent - review console")

    runs = store.available_runs()
    if not runs:
        st.sidebar.error("No runs found. Run `python -m eval.harness` first.")
        st.stop()

    labels = [f"{system} - {model} ({n})" for system, model, n in runs]
    chosen = st.sidebar.selectbox("Run", labels, index=0)
    system, model, _ = runs[labels.index(chosen)]

    view = st.sidebar.radio(
        "View", ["Review queue", "All submissions", "Results", "About"], index=0
    )
    st.sidebar.divider()
    st.sidebar.markdown(
        "<span class='kr-muted'>Triage and draft, never autonomous final grading. "
        "The agent defers what it is unsure of; a human decides those.</span>",
        unsafe_allow_html=True,
    )
    return view, system, model


def score_split(item: store.ReviewItem) -> None:
    """The architecture made visible: the model owns one of these, and it is
    the smallest."""
    st.markdown("**Where the score came from**")
    for name, value, source in (
        ("Correctness", item.score["correctness"], "S1 test suite"),
        ("Style", item.score["style"], "S2 ruff + radon"),
        ("Design", item.score["design"], "S4 model"),
    ):
        st.progress(min(1.0, max(0.0, value)), text=f"{name} {value:.2f} - {source}")


def render_item(item: store.ReviewItem, decided: dict) -> None:
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown(f"**{item.id}**")
        st.caption(item.problem.title)
        st.markdown(
            code_with_span(item.submission.source, item.evidence_span), unsafe_allow_html=True
        )

    with right:
        st.markdown(
            band_pill(item.score["band"])
            + f" &nbsp; <span class='kr-muted'>total {item.score['total']:.3f}</span>",
            unsafe_allow_html=True,
        )
        score_split(item)

        diagnosis = item.diagnosis
        if diagnosis:
            span = item.evidence_span
            where = f"lines {span[0]}-{span[1]}" if span else "no span"
            confidence = diagnosis.get("confidence", 0.0)
            st.markdown(
                f"**Diagnosis** <span class='kr-chip'>{diagnosis['label']}</span>"
                f"<span class='kr-muted'>{where}, confidence {confidence:.2f}</span>",
                unsafe_allow_html=True,
            )
            st.caption(diagnosis.get("rationale", ""))
        else:
            st.warning("No usable diagnosis: the model cited lines that do not exist.")

        if item.true_label:
            verdict = "matches" if item.agrees_with_truth else "differs from"
            st.markdown(
                "<span class='kr-muted'>Ground truth "
                f"<span class='kr-chip'>{item.true_label}</span> band {item.true_band}, "
                f"{verdict} the agent</span>",
                unsafe_allow_html=True,
            )
        if item.is_false_positive:
            st.error("False positive: correct work graded as buggy.")

        if item.feedback:
            with st.expander("Draft feedback for the student"):
                st.write(item.feedback)
                st.caption("Checked against the reference solution before display.")

    if item.deferred:
        st.info("**Deferred to you** - " + str(item.record.get("route_reason", "unspecified")))
        decision_form(item, decided)
    st.divider()


def decision_form(item: store.ReviewItem, decided: dict) -> None:
    previous = decided.get(item.id)
    if previous:
        note = previous.get("note")
        st.success(
            f"Recorded: **{previous['verdict']}**, final band **{previous['final_band']}**"
            + (f" - {note}" if note else "")
        )
        return

    with st.form("decide::" + item.id):
        columns = st.columns([1, 1, 3])
        bands = list(BAND_COLOURS)
        band = columns[0].selectbox("Final band", bands, index=bands.index(item.score["band"]))
        verdict = columns[1].selectbox("Verdict", ["agree", "override", "needs a second look"])
        note = columns[2].text_input("Note (optional)")
        if st.form_submit_button("Record decision"):
            store.record_decision(item, verdict, band, note)
            st.rerun()


def review_queue(queue: store.Queue) -> None:
    st.title("Review queue")
    decided = store.decisions()
    pending = [i for i in queue.deferred if i.id not in decided]

    columns = st.columns(4)
    columns[0].metric("Deferred to a human", len(queue.deferred))
    columns[1].metric("Still pending", len(pending))
    columns[2].metric("Auto-graded", len(queue.auto_graded))
    columns[3].metric(
        "Coverage",
        f"{len(queue.auto_graded) / max(1, len(queue.items)):.0%}",
        help="Share graded without a human. The rest is what the agent declined.",
    )

    if not queue.deferred:
        st.success("Nothing deferred in this run.")
        return

    show_all = st.checkbox("Include decisions already recorded", value=False)
    for item in queue.deferred if show_all else pending:
        render_item(item, decided)
    if not show_all and not pending:
        st.success("Queue clear: every deferred submission has a recorded decision.")


def all_submissions(queue: store.Queue) -> None:
    st.title("All submissions")
    labels = sorted({i.true_label for i in queue.items if i.true_label})
    columns = st.columns([2, 2, 2])
    label_filter = columns[0].multiselect("Ground-truth label", labels)
    only_wrong = columns[1].checkbox("Only where the agent disagrees with ground truth")
    only_fp = columns[2].checkbox("Only false positives on correct work")

    items = queue.items
    if label_filter:
        items = [i for i in items if i.true_label in label_filter]
    if only_wrong:
        items = [i for i in items if i.agrees_with_truth is False]
    if only_fp:
        items = [i for i in items if i.is_false_positive]

    st.caption(f"{len(items)} of {len(queue.items)} submissions")
    decided = store.decisions()
    for item in items[:60]:
        render_item(item, decided)
    if len(items) > 60:
        st.caption("Showing the first 60. Narrow the filters to see more.")


def results() -> None:
    st.title("Results")
    summary = store.load_summary()
    if not summary:
        st.warning("No summary.json yet. Run `python -m eval.harness`.")
        return

    rows = []
    for system in ("test_only", "static_only", "zero_shot_llm", "full_agent"):
        if system not in summary:
            continue
        s = summary[system]
        rows.append(
            {
                "System": system,
                "Band acc": round(s.get("band_accuracy", 0), 3),
                "Macro-F1": round(s.get("macro_f1", 0), 3),
                "FP on correct": round(s.get("fp_rate_on_correct", 0), 3),
                "Acc @70%": round(s.get("accuracy_at_70pct_coverage", 0), 3),
                "ECE": round(s.get("ece", 0), 3),
                "Deferred": round(s.get("deferral_rate", 0), 3),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(
        "Band accuracy is near-tautological on synthetic data: ground truth is "
        "rule-derived from the same tests the baselines read. Macro-F1 and the "
        "false-positive rate on correct code are the metrics that discriminate."
    )

    figures = store.RESULTS / "figures"
    if figures.exists():
        st.subheader("Figures")
        pair = st.columns(2)
        names = [
            "false_positive_rate.png",
            "risk_coverage.png",
            "per_class_f1.png",
            "confusion_matrix.png",
        ]
        for index, name in enumerate(names):
            path = figures / name
            if path.exists():
                pair[index % 2].image(str(path), use_container_width=True)

    adversarial = store.load_adversarial()
    if adversarial:
        st.subheader("Prompt-injection resistance")
        st.dataframe(
            [
                {
                    "Architecture": arm,
                    "Attack success": f"{data['overall']:.0%}",
                    "Routed to a human": f"{data['deferral_rate']:.0%}",
                }
                for arm, data in adversarial.get("arms", {}).items()
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            f"{adversarial.get('n_submissions', '?')} submissions x 8 attack families, "
            "each paired with a clean control on the same model."
        )


def about() -> None:
    st.title("About this console")
    st.markdown(
        """
This is **triage and draft, never autonomous final grading**. The routing layer
exists so a person decides the hard cases, and this console is where that
happens.

**What the agent decided, and what it did not.** Correctness comes from a
sandboxed test suite and style from ruff and radon; neither touches the model.
The model contributes one sub-score, design, weighted 15%. The bars on each
submission show that split, because it is the whole architectural argument.

**Every diagnosis cites lines.** A diagnosis pointing at a line that does not
exist is rejected upstream and becomes a deferral, so any highlight here was
validated against that exact file.

**Your decisions are kept separate.** They append to
`results/human_decisions.jsonl` and never modify the agent's output, so the two
cannot be confused when the numbers are recomputed.

**Known limits, from `results/REPORT.md`.** The agent is shown the reference
solution and every submission is a small edit to it, so diagnosis is partly a
diff-reading task; the measured macro-F1 of 0.933 should be expected to fall on
real student work. The false-positive rate on correct code is 0.056, not zero:
it penalised two correct submissions for writing a defensive idiom
unconventionally.
        """
    )


def main() -> None:
    view, system, model = sidebar()
    if view == "Results":
        results()
    elif view == "About":
        about()
    else:
        queue = cached_queue(system, model)
        if view == "Review queue":
            review_queue(queue)
        else:
            all_submissions(queue)


main()
