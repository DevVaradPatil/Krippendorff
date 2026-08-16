"""`OK` and `ALT`: transformations that change the code without breaking it.

These are the false-positive tests, and they are the most important operators in
the file. `OK` degrades presentation while leaving behaviour identical -- stripped
comments, single-letter names, dead code. `ALT` is a genuinely different correct
implementation, taken from the problem's ``alternative.py``.

Every variant produced here **must still pass the entire test suite**. The
generator asserts that and discards anything that does not, because an `OK`
sample that secretly fails a test would quietly turn the headline
false-positive number into nonsense.
"""

from __future__ import annotations

import ast
import builtins
import io
import keyword
import tokenize

# Names that must survive renaming: the tests call these by name, and the module
# constants are referenced from more than one scope.
_PROTECTED_BUILTINS = frozenset(dir(builtins))


def strip_comments_and_docstrings(source: str) -> str:
    """Remove every comment and docstring, keeping the code itself intact."""
    tree = ast.parse(source)
    docstring_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)):
            continue
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            first = node.body[0]
            docstring_lines.update(range(first.lineno, first.end_lineno + 1))

    out: list[str] = []
    for index, line in enumerate(source.splitlines(), start=1):
        if index in docstring_lines:
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        code = _drop_trailing_comment(line)
        if code.strip() == "" and stripped != "":
            continue
        out.append(code.rstrip())
    return "\n".join(out).strip() + "\n"


def _drop_trailing_comment(line: str) -> str:
    """Remove a trailing comment without cutting inside a string literal."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(line).readline))
    except (tokenize.TokenError, IndentationError):
        return line
    for token in tokens:
        if token.type == tokenize.COMMENT:
            return line[: token.start[1]]
    return line


def rename_locals(source: str) -> str:
    """Rename parameters and local variables to single letters."""
    tree = ast.parse(source)
    module_names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)} | {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    locals_found: list[str] = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for arg in func.args.args:
            locals_found.append(arg.arg)
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                locals_found.append(node.id)

    # Anything called with a keyword argument keeps its name: renaming the
    # parameter would break the call site.
    keyword_names = {
        kw.arg
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for kw in node.keywords
        if kw.arg
    }

    renamable = [
        name
        for name in dict.fromkeys(locals_found)
        if name not in module_names
        and name not in keyword_names
        and name not in _PROTECTED_BUILTINS
        and not keyword.iskeyword(name)
        and len(name) > 1
        and not name.startswith("_")
    ]
    # Fresh letters only. Renaming `total` to `a` in a function that already has
    # a parameter `a` silently changes behaviour, which would produce an "OK"
    # sample that fails its own tests.
    taken = {
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.NAME
    }
    mapping: dict[str, str] = {}
    for name in renamable:
        fresh = _next_free_name(taken)
        if fresh is None:
            break
        mapping[name] = fresh
        taken.add(fresh)

    if not mapping:
        return source
    return _rename_tokens(source, mapping)


def _next_free_name(taken: set[str]) -> str | None:
    for suffix in range(0, 10):
        for letter in "abcdefghijklmnopqrstuvwxyz":
            candidate = letter if suffix == 0 else f"{letter}{suffix}"
            if candidate not in taken:
                return candidate
    return None


def _rename_tokens(source: str, mapping: dict[str, str]) -> str:
    """Token-level rename: never touches attributes, strings, or comments."""
    out: list[str] = []
    previous_was_dot = False
    result_line, result_col = 1, 0
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.start[0] > result_line:
            out.append("\n" * (token.start[0] - result_line))
            result_line, result_col = token.start[0], 0
        if token.start[1] > result_col:
            out.append(" " * (token.start[1] - result_col))
            result_col = token.start[1]

        text = token.string
        if token.type == tokenize.NAME and not previous_was_dot and text in mapping:
            text = mapping[text]
        out.append(text)
        result_line, result_col = token.end
        previous_was_dot = token.type == tokenize.OP and token.string == "."
    return "".join(out)


_DEAD_CODE = [
    "    unused_total = 0",
    "    if False:",
    "        unused_total = unused_total + 1",
]


def add_dead_code(source: str) -> str:
    """Insert unreachable and unused statements into every function body."""
    lines = source.splitlines()
    tree = ast.parse(source)
    insert_at: list[int] = []
    for func in ast.walk(tree):
        if isinstance(func, ast.FunctionDef) and func.body:
            insert_at.append(func.body[0].lineno - 1)
    for line_index in sorted(insert_at, reverse=True):
        lines[line_index:line_index] = _DEAD_CODE
    return "\n".join(lines) + "\n"


def ok_variants(source: str) -> list[tuple[str, str]]:
    """Style-degraded but behaviourally identical versions of `source`."""
    stripped = strip_comments_and_docstrings(source)
    renamed = rename_locals(source)
    both = rename_locals(stripped)
    return [
        ("ok_no_comments", stripped),
        ("ok_single_letter_names", renamed),
        ("ok_stripped_and_renamed", both),
        ("ok_dead_code", add_dead_code(stripped)),
    ]
