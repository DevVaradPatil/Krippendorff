'''Tests for secant_root.

The secant method converges superlinearly, so a handful of iterations already
lands close. The tolerances below are tight enough that a fixed small iteration
count misses while an honest convergence check passes.
'''


def _quadratic(x):
    return x * x - 2.0


def _cubic(x):
    return x * x * x - x - 2.0


def _linear(x):
    return 3.0 * x - 6.0


def normal_sqrt_two(m):
    assert abs(m.secant(_quadratic, 0.0, 2.0) - 1.4142135623730951) < 1e-9


def normal_cubic(m):
    assert abs(_cubic(m.secant(_cubic, 1.0, 2.0))) < 1e-8


def normal_linear_is_exact(m):
    assert abs(m.secant(_linear, 0.0, 10.0) - 2.0) < 1e-9


def boundary_start_at_the_root(m):
    assert abs(m.secant(_linear, 2.0, 5.0) - 2.0) < 1e-9


def edge_loose_tolerance(m):
    assert abs(m.secant(_quadratic, 0.0, 2.0, 0.0001) - 1.4142135623730951) < 0.001


def edge_wide_bracket(m):
    # Asymmetric on purpose: f(-5) and f(5) are equal for this parabola, so no
    # secant line exists through them and the method has nothing to work with.
    root = m.secant(_quadratic, 0.5, 5.0)
    assert abs(root * root - 2.0) < 1e-6


def degenerate_equal_start_points(m):
    try:
        m.secant(_quadratic, 1.0, 1.0)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for equal starting points')


TESTS = [
    {'id': 'normal_sqrt_two', 'kind': 'normal', 'fn': normal_sqrt_two},
    {'id': 'normal_cubic', 'kind': 'normal', 'fn': normal_cubic},
    {'id': 'normal_linear_is_exact', 'kind': 'normal', 'fn': normal_linear_is_exact},
    {'id': 'boundary_start_at_the_root', 'kind': 'boundary', 'fn': boundary_start_at_the_root},
    {'id': 'edge_loose_tolerance', 'kind': 'edge', 'fn': edge_loose_tolerance},
    {'id': 'edge_wide_bracket', 'kind': 'edge', 'fn': edge_wide_bracket},
    {'id': 'degenerate_equal_start_points', 'kind': 'degenerate', 'fn': degenerate_equal_start_points},
]
