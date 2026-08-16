"""S3 - evidence bundle.

Assembles exactly what S4 is allowed to see, and separates trusted context from
untrusted student input.

Trusted: problem statement, rubric, reference solution, test results, static
features. Untrusted: the student's source, and -- held apart from it -- the
comments and docstrings stripped out of that source. Injections overwhelmingly
live in comments, so they are removed from the code the model reads and either
withheld entirely (the default) or passed as clearly-labelled untrusted data.

**Stripping preserves line numbering.** A comment line becomes a blank line and a
docstring becomes `...` padded with blank lines, rather than being deleted. That
costs nothing and removes an entire class of off-by-one bug: an evidence span
the model reports against the stripped code refers to the same line in the file
the student actually wrote, so no translation table is needed and none can drift.
"""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass, field

from agent.schemas import StaticFeatures, TestResult


@dataclass
class EvidenceBundle:
    problem_id: str
    problem_statement: str
    reference_solution: str
    #: Comments and docstrings removed; line numbering identical to the original.
    student_code_stripped: str
    #: Extracted comment text, never interpolated into the code block.
    student_comments: list[str] = field(default_factory=list)
    test_results: list[TestResult] = field(default_factory=list)
    static_features: StaticFeatures | None = None
    #: Whether the caller intends the comments to be shown to the model at all.
    include_comments: bool = False

    @property
    def failed_tests(self) -> list[TestResult]:
        return [r for r in self.test_results if not r.passed]


def strip_comments(source: str) -> tuple[str, list[str]]:
    """Return (code with comments and docstrings blanked, the removed text).

    Line count is unchanged, so line N of the result is line N of the input.
    """
    extracted: list[str] = []
    lines = source.splitlines()
    blanked: set[int] = set()
    replacements: dict[int, str] = {}

    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None

    if tree is not None:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Module | ast.FunctionDef | ast.ClassDef):
                continue
            docstring = _docstring_node(node)
            if docstring is None:
                continue
            extracted.append(str(docstring.value.value).strip())
            indent = " " * docstring.col_offset
            # `...` keeps a function whose entire body was a docstring valid.
            replacements[docstring.lineno] = f"{indent}..."
            blanked.update(range(docstring.lineno + 1, docstring.end_lineno + 1))

    for token in _comment_tokens(source):
        line_index = token.start[0]
        text = token.string.lstrip("#").strip()
        if text:
            extracted.append(text)
        if line_index in replacements or line_index in blanked:
            continue
        before = lines[line_index - 1][: token.start[1]]
        replacements[line_index] = before.rstrip() if before.strip() else ""

    out = []
    for number, line in enumerate(lines, start=1):
        if number in replacements:
            out.append(replacements[number])
        elif number in blanked:
            out.append("")
        else:
            out.append(line)
    return "\n".join(out) + "\n", extracted


def _docstring_node(node: ast.AST) -> ast.Expr | None:
    body = getattr(node, "body", None)
    if not body:
        return None
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return first
    return None


def _comment_tokens(source: str):
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                yield token
    except (tokenize.TokenError, IndentationError):
        return


def build(
    *,
    problem_id: str,
    problem_statement: str,
    reference_solution: str,
    source: str,
    results: list[TestResult],
    features: StaticFeatures,
    include_comments: bool = False,
) -> EvidenceBundle:
    stripped, comments = strip_comments(source)
    return EvidenceBundle(
        problem_id=problem_id,
        problem_statement=problem_statement,
        reference_solution=reference_solution,
        student_code_stripped=stripped,
        student_comments=comments,
        test_results=results,
        static_features=features,
        include_comments=include_comments,
    )
