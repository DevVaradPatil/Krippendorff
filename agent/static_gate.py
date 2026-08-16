"""S0 - static gate.

Cheapest possible rejection: parse the source, reject anything that will not
compile, and refuse imports outside the allowlist before a container is ever
started. A failure here exits the pipeline with a structured "did not compile"
result; it never reaches the LLM.

Nothing here executes the submission -- `ast.parse` only reads it.
"""

from __future__ import annotations

import ast

from pydantic import BaseModel

# Everything the intro problems legitimately need. Anything else is either a
# mistake or an attempt to reach outside the sandbox.
DEFAULT_IMPORT_ALLOWLIST = frozenset(
    {
        "math",
        "cmath",
        "random",
        "itertools",
        "functools",
        "collections",
        "statistics",
        "decimal",
        "fractions",
        "string",
        "re",
        "copy",
        "typing",
        "numpy",
        "matplotlib",
    }
)

# Names that only appear in intro-Python submissions by accident or by attack.
BANNED_CALLS = frozenset({"eval", "exec", "compile", "__import__", "globals", "vars"})


class GateResult(BaseModel):
    passed: bool
    syntax_error: str | None = None
    disallowed_imports: list[str] = []
    banned_constructs: list[str] = []


def _root_module(name: str) -> str:
    return name.split(".")[0]


def check(source: str, allowlist: frozenset[str] = DEFAULT_IMPORT_ALLOWLIST) -> GateResult:
    """Parse `source` and screen its imports. Never executes anything."""
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return GateResult(passed=False, syntax_error=f"{exc.msg} (line {exc.lineno})")

    disallowed: list[str] = []
    banned: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _root_module(alias.name) not in allowlist:
                    disallowed.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and _root_module(node.module) not in allowlist:
                disallowed.append(node.module)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in BANNED_CALLS
        ):
            banned.append(f"{node.func.id}() at line {node.lineno}")

    return GateResult(
        passed=not disallowed and not banned,
        disallowed_imports=sorted(set(disallowed)),
        banned_constructs=sorted(set(banned)),
    )
