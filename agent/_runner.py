"""Test runner. Executes INSIDE the sandbox container, never on the host.

The host process must never import this module -- it exists to be copied into a
container and run there alongside untrusted code.

Two things here are defenses rather than conveniences:

*Student stdout never reaches our stdout.* Everything the submission prints is
captured into a buffer. A submission that prints a convincing "5 passed" report
(the fake-test-output attack family) is writing into that buffer, not into the
channel we parse.

*Results are tagged with a nonce that the submission cannot read.* The nonce is
popped out of the environment before any student code is imported, and results
are written straight to fd 1 rather than through ``sys.stdout``, which the
submission is free to replace. Forging the results line therefore requires
guessing a random token.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import signal
import sys
import time
import traceback

# Popped, not read: after these two lines the values are gone from os.environ
# and the submission -- which runs in this same process -- cannot see them.
NONCE = os.environ.pop("KRIPP_NONCE", "")
CASE_TIMEOUT = float(os.environ.pop("KRIPP_CASE_TIMEOUT", "5"))

MAX_CAPTURE = 2000
WORK = "/work"


class CaseTimeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise CaseTimeout("case exceeded time limit")


def _load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _truncate(text: str) -> str:
    return text if len(text) <= MAX_CAPTURE else text[:MAX_CAPTURE] + "...[truncated]"


def main() -> None:
    signal.signal(signal.SIGALRM, _on_alarm)

    # Trusted first. Loading the test suite before the submission means student
    # code cannot monkeypatch the cases that are about to judge it.
    tests = _load(f"{WORK}/tests.py", "kripp_tests")
    cases = list(getattr(tests, "TESTS", []))

    buf = io.StringIO()
    import_error = None
    module = None

    signal.setitimer(signal.ITIMER_REAL, CASE_TIMEOUT)
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            module = _load(f"{WORK}/submission.py", "submission")
    except BaseException:
        import_error = traceback.format_exc(limit=6)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)

    results = []
    for case in cases:
        record = {
            "test_id": case["id"],
            "kind": case.get("kind", "normal"),
            "passed": False,
            "traceback": import_error,
            "stdout": "",
            "duration_s": 0.0,
            "timed_out": False,
        }
        if import_error is None:
            buf.seek(0)
            buf.truncate(0)
            started = time.monotonic()
            signal.setitimer(signal.ITIMER_REAL, CASE_TIMEOUT)
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    case["fn"](module)
                record["passed"] = True
                record["traceback"] = None
            except CaseTimeout:
                record["timed_out"] = True
                record["traceback"] = "TimeoutError: case exceeded time limit"
            except BaseException:
                record["traceback"] = traceback.format_exc(limit=6)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                record["duration_s"] = round(time.monotonic() - started, 4)
                record["stdout"] = _truncate(buf.getvalue())
        results.append(record)

    payload = json.dumps({"schema": 1, "import_error": import_error, "cases": results})
    # fd 1 directly: sys.stdout may have been replaced by the submission.
    os.write(1, (NONCE + payload + "\n").encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
