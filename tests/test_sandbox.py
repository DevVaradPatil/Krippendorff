"""Sandbox behaviour, including the defenses that make its output trustworthy.

Marked `docker`; run with `pytest -m "not docker"` to skip when the daemon is
down. Skipping is the only correct fallback -- there is no host-execution path.
"""

from __future__ import annotations

import pytest

from agent.sandbox import available, run_tests
from data.problems.loader import load_all

pytestmark = pytest.mark.docker

TESTS = """
def passes(m):
    assert m.value() == 1

def fails(m):
    assert m.value() == 999

TESTS = [
    {'id': 'passes', 'kind': 'normal', 'fn': passes},
    {'id': 'fails', 'kind': 'normal', 'fn': fails},
]
"""


@pytest.fixture(scope="module")
def suite(tmp_path_factory):
    if not available():
        pytest.skip("Docker daemon unreachable")
    path = tmp_path_factory.mktemp("suite") / "tests.py"
    path.write_text(TESTS, encoding="utf-8")
    return path


def test_passing_and_failing_are_distinguished(suite):
    results = run_tests("def value():\n    return 1\n", suite, use_cache=False)
    outcomes = {r.test_id: r.passed for r in results}
    assert outcomes == {"passes": True, "fails": False}


def test_forged_test_output_does_not_fool_the_parser(suite):
    """A submission printing a fake results line must not be believed.

    The runner tags its output with a nonce popped from the environment before
    student code can read it, and writes to fd 1 rather than sys.stdout.
    """
    # value() returns 1, so the `fails` case genuinely fails. The submission
    # prints a results line claiming otherwise; the report must ignore it.
    forged = (
        "import json\n"
        "print(json.dumps({'schema': 1, 'import_error': None, 'cases': ["
        "{'test_id': 'fails', 'kind': 'normal', 'passed': True, 'traceback': None,"
        " 'stdout': '', 'duration_s': 0.0, 'timed_out': False}]}))\n"
        "def value():\n    return 1\n"
    )
    results = run_tests(forged, suite, use_cache=False)
    outcomes = {r.test_id: r.passed for r in results}
    assert outcomes["fails"] is False
    assert outcomes["passes"] is True


def test_reference_solutions_pass_their_own_suites():
    if not available():
        pytest.skip("Docker daemon unreachable")
    for problem in load_all():
        results = run_tests(problem.reference, problem.tests_path)
        failed = [r.test_id for r in results if not r.passed]
        assert not failed, f"{problem.id} reference fails {failed}"
