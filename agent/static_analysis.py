"""S2 - deterministic feature extraction.

ruff for style violations, radon for complexity and maintainability, `ast` and
`tokenize` for structural metrics. Everything the style and documentation
criteria need comes from here and from nowhere else -- the LLM is never asked to
judge style.

Nothing in this stage executes the submission. ruff and radon parse it; they do
not run it, which is why this is safe to do on the host while S1 is not.
"""

from __future__ import annotations

import ast
import io
import json
import shutil
import subprocess
import sys
import tokenize

from agent.schemas import StaticFeatures

_RUFF = shutil.which("ruff")
_RULES = "E,F,W,B,SIM,C90"


def extract(source: str) -> StaticFeatures:
    """Compute style and complexity features. No execution, no model call."""
    features = StaticFeatures(
        ruff_violations=_ruff_violations(source),
        loc=_logical_lines(source),
        comment_ratio=_comment_ratio(source),
    )
    _add_ast_metrics(source, features)
    _add_radon_metrics(source, features)
    return features


def _ruff_violations(source: str) -> dict[str, int]:
    command = ([_RUFF] if _RUFF else [sys.executable, "-m", "ruff"]) + [
        "check",
        "--no-cache",
        "--select",
        _RULES,
        "--output-format",
        "json",
        "--stdin-filename",
        "submission.py",
        "-",
    ]
    try:
        completed = subprocess.run(
            command, input=source, capture_output=True, text=True, timeout=60
        )
        findings = json.loads(completed.stdout or "[]")
    except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return {}

    counts: dict[str, int] = {}
    for finding in findings:
        code = finding.get("code") or "UNKNOWN"
        counts[code] = counts.get(code, 0) + 1
    return counts


def _logical_lines(source: str) -> int:
    return sum(
        1 for line in source.splitlines() if line.strip() and not line.strip().startswith("#")
    )


def _comment_ratio(source: str) -> float:
    lines = max(1, len(source.splitlines()))
    comments = 0
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments += 1
    except (tokenize.TokenError, IndentationError):
        return 0.0
    return comments / lines


def _add_ast_metrics(source: str, features: StaticFeatures) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    documented = sum(1 for f in functions if ast.get_docstring(f))
    # The module docstring counts as one more documentable unit, so a file with
    # no functions still has a meaningful coverage number.
    total_units = len(functions) + 1
    documented += 1 if ast.get_docstring(tree) else 0
    features.function_count = len(functions)
    features.docstring_coverage = documented / total_units


def _add_radon_metrics(source: str, features: StaticFeatures) -> None:
    try:
        from radon.complexity import cc_visit
        from radon.metrics import mi_visit
    except ImportError:  # pragma: no cover - optional at runtime
        return
    try:
        blocks = cc_visit(source)
        features.cyclomatic_complexity = (
            max(block.complexity for block in blocks) if blocks else 1.0
        )
        features.maintainability_index = mi_visit(source, multi=True)
    except (SyntaxError, ValueError):
        return
