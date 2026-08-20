"""Mutation operators - one per misconception, each carrying its ground truth.

This is where the evaluation's credibility comes from. Because we know exactly
which mutation was applied and which tests it breaks, the rubric score is
computed by rule (``agent.aggregate.ground_truth_score``) rather than guessed at
by a human.

Two implementation choices are load-bearing:

**Sites are found on the AST, edits are applied to the source text.** Finding
sites by regex would eventually match inside a string literal and mislabel the
result. But rewriting the whole tree with ``ast.unparse`` would discard every
comment in the file -- which would silently destroy the documentation criterion
and make the OK operator's comment-stripping meaningless. So operators locate a
node, then splice replacement text over exactly that node's source span.

**One mutant per site, not one per operator.** An operator that matches three
`range()` calls yields three distinct submissions, which is how a 10-problem
benchmark reaches 300 labelled items without 25 hand-written problems.

``OK`` and ``ALT`` are mutations too: they change the code without breaking it,
and they are the false-positive tests. Keep them at ~20% of the generated set.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass

from agent.schemas import Misconception, Span


@dataclass(frozen=True)
class Edit:
    """A byte-range replacement in the source text. `new_text` empty = deletion."""

    start: int
    end: int
    new_text: str


@dataclass(frozen=True)
class Mutant:
    """One generated submission-to-be, before its tests have been run."""

    operator_id: str
    label: Misconception
    source: str
    sites: list[Span]
    note: str = ""


@dataclass(frozen=True)
class MutationOperator:
    id: str
    label: Misconception
    description: str
    find: Callable[[ast.Module, str], list[list[Edit]]]
    #: Filled in by the generator, never asserted by hand.
    severity_from_tests: bool = True


REGISTRY: dict[str, MutationOperator] = {}


def register(op: MutationOperator) -> MutationOperator:
    if op.id in REGISTRY:
        raise ValueError(f"duplicate mutation operator id: {op.id}")
    REGISTRY[op.id] = op
    return op


# --- source-splicing helpers ------------------------------------------------


def _line_starts(source: str) -> list[int]:
    starts = [0]
    for i, ch in enumerate(source):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _pos(source: str, lineno: int, col: int) -> int:
    return _line_starts(source)[lineno - 1] + col


def _node_span(source: str, node: ast.AST) -> tuple[int, int]:
    return (
        _pos(source, node.lineno, node.col_offset),
        _pos(source, node.end_lineno, node.end_col_offset),
    )


def _seg(source: str, node: ast.AST) -> str:
    start, end = _node_span(source, node)
    return source[start:end]


def replace(source: str, node: ast.AST, new_text: str) -> Edit:
    start, end = _node_span(source, node)
    return Edit(start, end, new_text)


def delete_statement(source: str, node: ast.stmt) -> Edit:
    """Delete a whole statement including its indentation and trailing newline."""
    starts = _line_starts(source)
    start = starts[node.lineno - 1]
    end = starts[node.end_lineno] if node.end_lineno < len(starts) else len(source)
    return Edit(start, end, "")


def apply_edits(source: str, edits: list[Edit]) -> tuple[str, list[Span]]:
    """Apply edits and report where they landed in the *mutated* source."""
    out = source
    for edit in sorted(edits, key=lambda e: e.start, reverse=True):
        out = out[: edit.start] + edit.new_text + out[edit.end :]

    spans: list[Span] = []
    for edit in sorted(edits, key=lambda e: e.start):
        # Line numbers shift below a deletion, so locate the edit in the result.
        line = out.count("\n", 0, min(edit.start, len(out))) + 1
        end_line = out.count("\n", 0, min(edit.start + len(edit.new_text), len(out))) + 1
        line = min(line, out.count("\n") + 1)
        spans.append(Span(start_line=line, end_line=max(line, end_line)))
    return out, spans


# --- operators --------------------------------------------------------------


def _names_in(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _walk_calls(tree: ast.AST, name: str) -> list[ast.Call]:
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == name
    ]


def _find_obo(tree: ast.Module, source: str) -> list[list[Edit]]:
    """Shift a loop or index bound by one.

    Two site kinds: the bound of a `range()` call, and any `len(x) +/- 1`, which
    is where the inclusive/exclusive mix-up usually lives.
    """
    out = []
    for call in _walk_calls(tree, "range"):
        if not call.args:
            continue
        bound = call.args[1] if len(call.args) >= 2 else call.args[0]
        if (
            isinstance(bound, ast.BinOp)
            and isinstance(bound.op, ast.Add)
            and isinstance(bound.right, ast.Constant)
            and bound.right.value == 1
        ):
            out.append([replace(source, bound, _seg(source, bound.left))])
        else:
            out.append([replace(source, bound, f"{_seg(source, bound)} - 1")])

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, (ast.Add, ast.Sub))
            and isinstance(node.right, ast.Constant)
            and node.right.value == 1
            and isinstance(node.left, ast.Call)
            and isinstance(node.left.func, ast.Name)
            and node.left.func.id == "len"
        ):
            out.append([replace(source, node, _seg(source, node.left))])
    return out


_CMP_SWAP = {
    ast.LtE: ("<=", "<"),
    ast.Lt: ("<", "<="),
    ast.GtE: (">=", ">"),
    ast.Gt: (">", ">="),
    ast.Eq: ("==", "!="),
    ast.NotEq: ("!=", "=="),
}


def _find_cmp(tree: ast.Module, source: str) -> list[list[Edit]]:
    """Swap a comparison for its neighbour: `<=` -> `<`, `==` -> `!=`."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        swap = _CMP_SWAP.get(type(node.ops[0]))
        if swap is None:
            continue
        left = _seg(source, node.left)
        right = _seg(source, node.comparators[0])
        if "\n" in left or "\n" in right:
            continue
        out.append([replace(source, node, f"{left} {swap[1]} {right}")])
    return out


def _find_acc(tree: ast.Module, source: str) -> list[list[Edit]]:
    """An accumulator initialised to 1 instead of 0."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target, value = node.targets[0], node.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Constant):
            continue
        if value.value not in (0, 0.0) or isinstance(value.value, bool):
            continue
        replacement = "1.0" if isinstance(value.value, float) else "1"
        out.append([replace(source, value, replacement)])
    return out


def _find_div(tree: ast.Module, source: str) -> list[list[Edit]]:
    """True division swapped for floor division."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
            continue
        left, right = _seg(source, node.left), _seg(source, node.right)
        if "\n" in left or "\n" in right:
            continue
        out.append([replace(source, node, f"{left} // {right}")])
    return out


def _find_mut(tree: ast.Module, source: str) -> list[list[Edit]]:
    """`x=None` plus an `if x is None` guard becomes a shared mutable default."""
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        for default in func.args.defaults:
            if not (isinstance(default, ast.Constant) and default.value is None):
                continue
            index = func.args.defaults.index(default)
            arg = func.args.args[len(func.args.args) - len(func.args.defaults) + index]
            guard = _none_guard(func, arg.arg)
            if guard is None:
                continue
            literal = _seg(source, guard.body[0].value)
            out.append(
                [
                    replace(source, default, literal),
                    delete_statement(source, guard),
                ]
            )
    return out


def _none_guard(func: ast.FunctionDef, name: str) -> ast.If | None:
    """Find `if <name> is None: <name> = <mutable>` at the top of a function."""
    for stmt in func.body:
        if (
            isinstance(stmt, ast.If)
            and isinstance(stmt.test, ast.Compare)
            and isinstance(stmt.test.left, ast.Name)
            and stmt.test.left.id == name
            and len(stmt.test.ops) == 1
            and isinstance(stmt.test.ops[0], ast.Is)
            and len(stmt.body) == 1
            and isinstance(stmt.body[0], ast.Assign)
        ):
            return stmt
    return None


def _find_ali(tree: ast.Module, source: str) -> list[list[Edit]]:
    """Drop a defensive copy, or build rows that are all the same list object."""
    out = []
    for node in ast.walk(tree):
        # x.copy() -> x
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "copy"
            and not node.args
        ):
            out.append([replace(source, node, _seg(source, node.func.value))])
        # list(x) -> x
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "list"
            and len(node.args) == 1
        ):
            out.append([replace(source, node, _seg(source, node.args[0]))])
        # [expr for _ in range(n)] -> [expr] * n   (every row the same object)
        elif isinstance(node, ast.ListComp) and len(node.generators) == 1:
            gen = node.generators[0]
            if (
                isinstance(gen.target, ast.Name)
                and isinstance(gen.iter, ast.Call)
                and isinstance(gen.iter.func, ast.Name)
                and gen.iter.func.id == "range"
                and len(gen.iter.args) == 1
                # Only safe when the element does not depend on the loop
                # variable -- otherwise `[x] * n` is not an equivalent shape.
                and gen.target.id not in _names_in(node.elt)
            ):
                elt = _seg(source, node.elt)
                count = _seg(source, gen.iter.args[0])
                out.append([replace(source, node, f"[{elt}] * {count}")])
    return out


def _find_scp(tree: ast.Module, source: str) -> list[list[Edit]]:
    """Hoist a local accumulator to module scope; state then leaks across calls."""
    out = []
    for func in tree.body:
        if not isinstance(func, ast.FunctionDef):
            continue
        for stmt in func.body:
            if not (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, (int, float))
            ):
                continue
            name = stmt.targets[0].id
            if not _is_accumulated(func, name):
                continue
            init = _seg(source, stmt)
            declaration = replace(source, stmt, f"global {name}")
            # start == end: a pure insertion. An Edit whose end precedes its
            # start re-emits everything between them, which duplicated the
            # module docstring when this was Edit(offset, 0, ...).
            at = _module_body_start(tree, source)
            module_level = Edit(at, at, init + "\n")
            out.append([declaration, module_level])
    return out


def _module_body_start(tree: ast.Module, source: str) -> int:
    """Offset just after the module docstring, or 0 when there is none.

    Inserting at offset 0 puts the global *above* the docstring, which demotes it
    to an ordinary string expression and silently changes the documentation
    sub-score. A student writing a global would put it below the docstring, and
    a mutant should look like code someone might plausibly have written.
    """
    if not tree.body:
        return 0
    first = tree.body[0]
    is_docstring = (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    )
    if not is_docstring:
        return 0
    starts = _line_starts(source)
    return starts[first.end_lineno] if first.end_lineno < len(starts) else len(source)


def _is_accumulated(func: ast.FunctionDef, name: str) -> bool:
    """True if `name` is written again after its initialisation.

    Any re-assignment is enough: what makes hoisting the variable to module
    scope a bug is that its value survives the call, and `best = counts[word]`
    survives just as destructively as `total = total + x`.
    """
    writes = 0
    for node in ast.walk(func):
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            writes += node.target.id == name
        elif isinstance(node, ast.Assign):
            writes += any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    return writes > 1


def _find_rec(tree: ast.Module, source: str) -> list[list[Edit]]:
    """Delete the base case of a self-recursive function."""
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        calls_itself = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == func.name
            for n in ast.walk(func)
        )
        if not calls_itself:
            continue
        for stmt in func.body:
            # The base case returns either a literal (`return 1`) or one of the
            # parameters (`return a` in Euclid's algorithm); both terminate the
            # recursion, and matching only literals misses half the taxonomy.
            if (
                isinstance(stmt, ast.If)
                and len(stmt.body) == 1
                and isinstance(stmt.body[0], ast.Return)
                and isinstance(stmt.body[0].value, (ast.Constant, ast.Name))
                and not stmt.orelse
            ):
                out.append([delete_statement(source, stmt)])
    return out


def _find_loop(tree: ast.Module, source: str) -> list[list[Edit]]:
    """`continue` where the loop should keep going becomes an early `return`."""
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        returned = _returned_name(func)
        for node in ast.walk(func):
            if isinstance(node, ast.Continue):
                text = f"return {returned}" if returned else "return"
                out.append([replace(source, node, text)])
    return out


def _returned_name(func: ast.FunctionDef) -> str | None:
    for stmt in reversed(func.body):
        if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Name):
            return stmt.value.id
    return None


def _find_conv(tree: ast.Module, source: str) -> list[list[Edit]]:
    """Iterate a fixed handful of times instead of until the tolerance is met."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        iterates_a_bound = (
            isinstance(node.iter, ast.Call)
            and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range"
            and len(node.iter.args) == 1
        )
        if not iterates_a_bound:
            continue
        # Only a loop that can exit early is honouring a tolerance at all.
        has_early_exit = any(
            isinstance(inner, ast.Return)
            for stmt in node.body
            if isinstance(stmt, ast.If)
            for inner in ast.walk(stmt)
        )
        if has_early_exit:
            out.append([replace(source, node.iter.args[0], "3")])
    return out


def _find_edge(tree: ast.Module, source: str) -> list[list[Edit]]:
    """Delete a guard that rejects or short-circuits degenerate input."""
    out = []
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        # Guards are not always the first statement: validation inside a parsing
        # loop is a guard too, and only walking the top level misses it.
        for stmt in ast.walk(func):
            if not isinstance(stmt, ast.If) or stmt.orelse or len(stmt.body) != 1:
                continue
            inner = stmt.body[0]
            guards_input = isinstance(inner, ast.Raise) or (
                isinstance(inner, ast.Return)
                and isinstance(inner.value, (ast.List, ast.Dict))
                and not getattr(inner.value, "elts", None)
                and not getattr(inner.value, "keys", None)
            )
            if guards_input:
                out.append([delete_statement(source, stmt)])
    return out


def _find_type(tree: ast.Module, source: str) -> list[list[Edit]]:
    """Drop a numeric conversion, leaving a string where a number is expected."""
    out = []
    for name in ("float", "int"):
        for call in _walk_calls(tree, name):
            if len(call.args) == 1 and not isinstance(call.args[0], ast.Constant):
                out.append([replace(source, call, _seg(source, call.args[0]))])
    return out


_OPERATORS = [
    ("obo_range_bound", Misconception.OBO, "off-by-one in a range bound", _find_obo),
    ("cmp_operator_swap", Misconception.CMP, "wrong comparison operator", _find_cmp),
    ("acc_init_one", Misconception.ACC, "accumulator initialised to 1", _find_acc),
    ("div_floor", Misconception.DIV, "floor where true division is meant", _find_div),
    ("mut_default_arg", Misconception.MUT, "mutable default argument", _find_mut),
    ("ali_shared_reference", Misconception.ALI, "alias instead of a copy", _find_ali),
    ("scp_global_accumulator", Misconception.SCP, "accumulator made global", _find_scp),
    ("rec_missing_base_case", Misconception.REC, "base case removed", _find_rec),
    ("loop_early_return", Misconception.LOOP, "return where continue was meant", _find_loop),
    ("conv_fixed_iterations", Misconception.CONV, "fixed count, not a tolerance", _find_conv),
    ("edge_guard_removed", Misconception.EDGE, "input guard removed", _find_edge),
    ("type_conversion_dropped", Misconception.TYPE, "numeric conversion dropped", _find_type),
]

for _id, _label, _description, _find in _OPERATORS:
    register(MutationOperator(_id, _label, _description, _find))
