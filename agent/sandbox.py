"""S1 - sandboxed execution.

Runs the student's code against the problem's test suite inside Docker with
``--network none``, memory/CPU/PID caps, a hard wall-clock timeout, and **no
host mounts** -- the working files are streamed into the container as a tar
archive (``put_archive``) rather than bind-mounted, so nothing on the host is
reachable even in principle.

Untrusted code is never executed in this process. There is no ``exec()``
fallback and no "just this once on the host" path -- if Docker is unavailable
the correct behaviour is to fail loudly, because the results of this stage are
the ground truth that the entire evaluation rests on.

Results are cached on a hash of everything that could change them, so
generating the dataset and running the test-only baseline execute each distinct
(submission, suite) pair exactly once.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import secrets
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path

from agent.schemas import TestResult

_RUNNER = Path(__file__).resolve().parent / "_runner.py"
CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "sandbox"


@dataclass(frozen=True)
class SandboxLimits:
    timeout_s: float = 5.0  # per test case, enforced inside the container
    memory_mb: int = 256
    cpus: float = 1.0
    pids: int = 64
    image: str = "python:3.12-slim"
    wall_clock_s: float = 60.0  # backstop if the in-container alarm is swallowed


class SandboxUnavailableError(RuntimeError):
    """Raised when Docker is missing. Do not degrade to host execution."""


# `docker.from_env()` assumes the classic \\.\pipe\docker_engine endpoint, but
# Docker Desktop's default context ("desktop-linux") listens on
# dockerDesktopLinuxEngine instead, so the SDK cannot see a daemon the CLI is
# talking to happily. Try the documented endpoints in order rather than making
# every developer export DOCKER_HOST.
_ENDPOINTS = (
    "npipe:////./pipe/dockerDesktopLinuxEngine",  # Docker Desktop on Windows
    "npipe:////./pipe/docker_engine",  # Docker Engine on Windows
    "unix:///var/run/docker.sock",  # Linux / macOS
)


def _client():
    try:
        import docker
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise SandboxUnavailableError("docker SDK not installed") from exc

    attempts: list[str] = []
    candidates = [os.environ["DOCKER_HOST"]] if os.environ.get("DOCKER_HOST") else []
    candidates += [e for e in _ENDPOINTS if e not in candidates]

    for endpoint in candidates:
        try:
            client = docker.DockerClient(base_url=endpoint)
            client.ping()
            return client
        except Exception as exc:
            attempts.append(f"{endpoint}: {type(exc).__name__}")

    raise SandboxUnavailableError(
        "cannot reach the Docker daemon; start Docker Desktop. Never fall back "
        "to running untrusted code on the host. Tried:\n  " + "\n  ".join(attempts)
    )


def _tar(files: dict[str, bytes]) -> bytes:
    """Build an in-memory tar placing `files` under /work, world-readable."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        directory = tarfile.TarInfo("work")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o555
        tar.addfile(directory)
        for name, data in files.items():
            info = tarfile.TarInfo(f"work/{name}")
            info.size = len(data)
            info.mode = 0o444
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def cache_key(source: str, tests_source: str, limits: SandboxLimits) -> str:
    payload = json.dumps(
        {
            "source": source,
            "tests": tests_source,
            "runner": _RUNNER.read_text(encoding="utf-8"),
            "image": limits.image,
            "timeout_s": limits.timeout_s,
            "memory_mb": limits.memory_mb,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def run_tests(
    source: str,
    tests_path: Path,
    limits: SandboxLimits | None = None,
    *,
    use_cache: bool = True,
) -> list[TestResult]:
    """Execute `source` against the test suite; one TestResult per test case."""
    limits = limits or SandboxLimits()
    tests_source = Path(tests_path).read_text(encoding="utf-8")
    key = cache_key(source, tests_source, limits)
    cached = CACHE_DIR / f"{key}.json"
    if use_cache and cached.exists():
        return [TestResult(**r) for r in json.loads(cached.read_text(encoding="utf-8"))]

    results = _run_uncached(source, tests_source, limits)

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached.write_text(json.dumps([r.model_dump() for r in results], indent=1), encoding="utf-8")
    return results


def _run_uncached(source: str, tests_source: str, limits: SandboxLimits) -> list[TestResult]:
    client = _client()
    nonce = secrets.token_hex(16)

    archive = _tar(
        {
            "submission.py": source.encode("utf-8", "replace"),
            "tests.py": tests_source.encode("utf-8"),
            "runner.py": _RUNNER.read_bytes(),
        }
    )

    container = client.containers.create(
        limits.image,
        command=["python", "-I", "-B", "/work/runner.py"],
        network_disabled=True,
        mem_limit=f"{limits.memory_mb}m",
        nano_cpus=int(limits.cpus * 1e9),
        pids_limit=limits.pids,
        environment={"KRIPP_NONCE": nonce, "KRIPP_CASE_TIMEOUT": str(limits.timeout_s)},
        working_dir="/work",
        user="nobody",
        network_mode="none",
    )
    try:
        container.put_archive("/", archive)
        started = time.monotonic()
        container.start()
        timed_out = False
        try:
            container.wait(timeout=limits.wall_clock_s)
        except Exception:
            timed_out = True
            container.kill()
        elapsed = time.monotonic() - started
        raw = container.logs(stdout=True, stderr=False).decode("utf-8", "replace")
    finally:
        with contextlib.suppress(Exception):  # best-effort cleanup
            container.remove(force=True)

    return _parse(raw, nonce, timed_out, elapsed, tests_source)


def _parse(
    raw: str, nonce: str, timed_out: bool, elapsed: float, tests_source: str
) -> list[TestResult]:
    """Find the nonce-tagged results line. Anything else on stdout is noise."""
    for line in raw.splitlines():
        if line.startswith(nonce):
            payload = json.loads(line[len(nonce) :])
            return [
                TestResult(
                    test_id=c["test_id"],
                    kind=c["kind"],
                    passed=c["passed"],
                    stdout=c["stdout"],
                    traceback=c["traceback"],
                    duration_s=c["duration_s"],
                    timed_out=c["timed_out"],
                )
                for c in payload["cases"]
            ]

    # No trustworthy line: the process died, hit the wall clock, or the OOM
    # killer took it. Every case fails, and it fails as *infrastructure*, not as
    # a silently-passing submission.
    reason = "wall-clock timeout" if timed_out else "runner produced no result line"
    return [
        TestResult(
            test_id=test_id,
            kind="unknown",
            passed=False,
            traceback=f"sandbox: {reason}",
            duration_s=elapsed,
            timed_out=timed_out,
        )
        for test_id in _declared_test_ids(tests_source)
    ]


def _declared_test_ids(tests_source: str) -> list[str]:
    """Recover case ids from the suite without importing it on the host."""
    import ast

    ids: list[str] = []
    tree = ast.parse(tests_source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=False):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "id"
                    and isinstance(value, ast.Constant)
                ):
                    ids.append(value.value)
    return ids or ["unknown"]


def available() -> bool:
    """True if the sandbox can actually run. Used to skip tests, never to bypass."""
    try:
        _client()
        return True
    except SandboxUnavailableError:
        return False
