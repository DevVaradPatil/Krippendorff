"""S0 - static gate.

Cheapest possible rejection: parse the source, reject anything that will not
compile, and refuse imports outside the allowlist before a container is ever
started. A failure here exits the pipeline with a structured "did not compile"
result; it never reaches the LLM.
"""

from __future__ import annotations

from pydantic import BaseModel

# Everything the 25 intro problems legitimately need. Anything else is either a
# mistake or an attempt to reach outside the sandbox.
DEFAULT_IMPORT_ALLOWLIST = frozenset(
    {"math", "cmath", "random", "itertools", "functools", "collections",
     "statistics", "decimal", "fractions", "string", "re", "copy", "typing",
     "numpy", "matplotlib", "matplotlib.pyplot"}
)


class GateResult(BaseModel):
    passed: bool
    syntax_error: str | None = None
    disallowed_imports: list[str] = []


def check(source: str, allowlist: frozenset[str] = DEFAULT_IMPORT_ALLOWLIST) -> GateResult:
    """Parse `source` and screen its imports. Never executes anything."""
    raise NotImplementedError
