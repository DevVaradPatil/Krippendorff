'''Tests for trapezoid_integration.

The linear cases are the sharp ones: the trapezoidal rule is *exact* for a
straight line, so a tolerance of 1e-9 catches an off-by-one or a mis-initialised
accumulator that a loose tolerance on the quadratic case would let through.
'''


def _square(x):
    return x * x


def _double(x):
    return 2.0 * x


def normal_quadratic(m):
    assert abs(m.trapezoid(_square, 0.0, 1.0, 100) - 1.0 / 3.0) < 1e-3


def normal_linear_exact(m):
    assert abs(m.trapezoid(_double, 0.0, 3.0, 60) - 9.0) < 1e-9


def edge_single_interval(m):
    assert abs(m.trapezoid(_double, 0.0, 2.0, 1) - 4.0) < 1e-9


def boundary_zero_width(m):
    assert abs(m.trapezoid(_square, 2.0, 2.0, 10) - 0.0) < 1e-12


def boundary_fine_grid(m):
    assert abs(m.trapezoid(_square, 0.0, 1.0, 2000) - 1.0 / 3.0) < 1e-6


def degenerate_invalid_n(m):
    try:
        m.trapezoid(_square, 0.0, 1.0, 0)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for n = 0')


TESTS = [
    {'id': 'normal_quadratic', 'kind': 'normal', 'fn': normal_quadratic},
    {'id': 'normal_linear_exact', 'kind': 'normal', 'fn': normal_linear_exact},
    {'id': 'edge_single_interval', 'kind': 'edge', 'fn': edge_single_interval},
    {'id': 'boundary_zero_width', 'kind': 'boundary', 'fn': boundary_zero_width},
    {'id': 'boundary_fine_grid', 'kind': 'boundary', 'fn': boundary_fine_grid},
    {'id': 'degenerate_invalid_n', 'kind': 'degenerate', 'fn': degenerate_invalid_n},
]
