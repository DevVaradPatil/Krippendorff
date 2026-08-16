'''Tests for bisection_root.

`normal_sqrt2_tight` is the convergence test: a solution that runs a fixed
handful of iterations instead of honouring `tol` lands near the root but not
near enough, which is precisely the CONV misconception.
'''


def _quadratic(x):
    return x * x - 2.0


def _cubic(x):
    return x * x * x - x - 2.0


def _linear(x):
    return 3.0 * x - 6.0


def normal_sqrt2_tight(m):
    root = m.bisect(_quadratic, 0.0, 2.0)
    assert abs(root - 2.0 ** 0.5) < 1e-8


def normal_cubic(m):
    root = m.bisect(_cubic, 1.0, 2.0)
    assert abs(_cubic(root)) < 1e-6


def normal_linear(m):
    assert abs(m.bisect(_linear, 0.0, 10.0) - 2.0) < 1e-8


def edge_root_at_bracket_end(m):
    assert abs(m.bisect(_linear, 2.0, 5.0) - 2.0) < 1e-6


def edge_loose_tolerance(m):
    root = m.bisect(_quadratic, 0.0, 2.0, 1e-3)
    assert abs(root - 2.0 ** 0.5) < 1e-2


def degenerate_no_sign_change(m):
    try:
        m.bisect(_quadratic, 2.0, 5.0)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError when the bracket has no sign change')


TESTS = [
    {'id': 'normal_sqrt2_tight', 'kind': 'normal', 'fn': normal_sqrt2_tight},
    {'id': 'normal_cubic', 'kind': 'normal', 'fn': normal_cubic},
    {'id': 'normal_linear', 'kind': 'normal', 'fn': normal_linear},
    {'id': 'edge_root_at_bracket_end', 'kind': 'edge', 'fn': edge_root_at_bracket_end},
    {'id': 'edge_loose_tolerance', 'kind': 'edge', 'fn': edge_loose_tolerance},
    {'id': 'degenerate_no_sign_change', 'kind': 'degenerate', 'fn': degenerate_no_sign_change},
]
