"""The leak detector, which is the one thing feedback must never get wrong.

Both directions matter. A detector that misses a leak hands a student the answer.
A detector that fires on ordinary feedback silently replaces every response with
the template, which looks like working software and teaches nobody anything.
"""

from __future__ import annotations

import pytest

from agent.feedback import (
    MAX_OVERLAP_RATIO,
    leaks_solution,
    overlap_ratio,
    template_feedback,
    verbatim_lines,
)
from agent.schemas import Diagnosis, Misconception, Span

REFERENCE = '''"""Composite trapezoidal rule."""


def trapezoid(f, a, b, n):
    """Approximate the integral of f from a to b."""
    if n <= 0:
        raise ValueError('n must be a positive integer')
    h = (b - a) / n
    total = 0.0
    total = total + f(a) / 2.0
    total = total + f(b) / 2.0
    for i in range(1, n):
        total = total + f(a + i * h)
    return total * h
'''

GOOD_FEEDBACK = (
    "Your loop on line 12 runs from 1 up to but not including n. Trace it by hand "
    "with n = 2 and write down which sample points get added.\n\n"
    "How many interior points should a two-interval trapezoid rule use, and how "
    "many does your loop visit?\n\n"
    "Try printing each value of i inside the loop for a small n and compare that "
    "against the points you expected to sum."
)


class TestLeakIsCaught:
    def test_a_verbatim_reference_line(self):
        leaked = (
            "Your accumulator starts wrong. It should be:\n"
            "        total = total + f(a + i * h)\n"
            "Try that."
        )
        assert verbatim_lines(leaked, REFERENCE)
        assert leaks_solution(leaked, REFERENCE)

    def test_the_whole_solution_pasted(self):
        assert leaks_solution(f"Here is how it should look:\n{REFERENCE}", REFERENCE)

    def test_a_long_run_of_reference_code(self):
        leaked = (
            "Compare your version with this shape: h = (b - a) / n then "
            "total = 0.0 then total = total + f(a) / 2.0 and "
            "total = total + f(b) / 2.0 before the loop."
        )
        assert leaks_solution(leaked, REFERENCE)


class TestLegitimateFeedbackSurvives:
    def test_socratic_feedback_is_not_flagged(self):
        assert not leaks_solution(GOOD_FEEDBACK, REFERENCE)
        assert overlap_ratio(GOOD_FEEDBACK, REFERENCE) <= MAX_OVERLAP_RATIO

    def test_naming_an_identifier_is_not_a_leak(self):
        # Feedback has to be able to say "total" and "h" to be useful at all.
        text = "What does total hold before the loop starts, and what is h measuring?"
        assert not leaks_solution(text, REFERENCE)

    @pytest.mark.parametrize("shared", ["return total * h", "total = 0.0", "if n <= 0:"])
    def test_quoting_a_line_the_student_already_has_is_not_a_leak(self, shared):
        # The core move of useful feedback is quoting the student's own code back
        # at them. They cannot be handed something they already wrote, so the
        # detector subtracts their source from the reference before comparing.
        student = REFERENCE.replace("total = 0.0", "total = 1.0")
        text = f"Look at where you wrote {shared}"
        assert not verbatim_lines(text, REFERENCE, student)
        assert not leaks_solution(text, REFERENCE, student)

    def test_without_the_student_source_the_detector_stays_conservative(self):
        # Called with no submission to compare against, a substantial reference
        # line is treated as a leak rather than waved through.
        assert verbatim_lines("you need total = total + f(a + i * h)", REFERENCE)

    def test_a_line_the_student_lacks_is_still_caught(self):
        # The one that matters: the mutated line is exactly the fix, so quoting
        # the reference version of it hands over the answer.
        student = REFERENCE.replace("h = (b - a) / n", "h = (b - a) // n")
        assert leaks_solution("change it to h = (b - a) / n and retry", REFERENCE, student)

    def test_quoting_the_students_own_line_back_is_fine(self):
        text = "On line 9 you wrote total = 1.0 -- what does that mean for the sum?"
        assert not leaks_solution(text, REFERENCE)

    def test_empty_feedback_is_not_a_leak(self):
        assert not leaks_solution("", REFERENCE)


class TestDetectorHasMargin:
    """Both axes must actually be capable of firing, with room to spare.

    Measured on 15 real generated responses, the original overlap metric --
    share of the *feedback* resembling the reference -- peaked at 0.117 even for
    a solution pasted in whole, below its own 0.15 threshold. It could never have
    fired. Normalising over the reference instead gives a wide margin.
    """

    def test_a_pasted_solution_scores_far_above_the_threshold(self):
        student = REFERENCE.replace("total = 0.0", "total = 1.0")
        ratio = overlap_ratio(
            f"{GOOD_FEEDBACK}\n\nHere is a correct version:\n{REFERENCE}",
            REFERENCE,
            student,
        )
        assert ratio > 0.5, ratio

    def test_ordinary_feedback_scores_far_below_it(self):
        student = REFERENCE.replace("total = 0.0", "total = 1.0")
        assert overlap_ratio(GOOD_FEEDBACK, REFERENCE, student) < 0.05

    def test_numeric_literals_are_tokenised(self):
        # `if x < 0:` lost its `0` to the tokeniser, counted four tokens, fell
        # under the floor, and slipped through -- the removed-guard fix is the
        # shortest and most leakable line in the taxonomy.
        reference = "def f(x):\n    if x < 0:\n        raise ValueError('no')\n    return x\n"
        student = "def f(x):\n    return x\n"
        assert leaks_solution("write if x < 0: at the top", reference, student)


class TestTemplate:
    @pytest.mark.parametrize("label", list(Misconception))
    def test_every_label_has_a_usable_template(self, label):
        diagnosis = Diagnosis(
            label=label,
            evidence=[Span(start_line=4, end_line=6)],
            rationale="r",
            confidence=0.9,
        )
        text = template_feedback(diagnosis)
        assert "lines 4-6" in text
        assert not leaks_solution(text, REFERENCE)

    def test_a_single_line_span_reads_naturally(self):
        diagnosis = Diagnosis(
            label=Misconception.OBO,
            evidence=[Span(start_line=7, end_line=7)],
            rationale="r",
            confidence=0.9,
        )
        assert "line 7" in template_feedback(diagnosis)
        assert "lines 7-7" not in template_feedback(diagnosis)
