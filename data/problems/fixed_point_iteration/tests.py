'''Tests for fixed_point_iteration.

The Babylonian map converges quadratically, so three iterations already look
plausible. The tolerances below are tight enough to separate a genuine
convergence test from a loop that simply ran out of iterations.
'''


def _halving(x):
    return x / 2.0


def normal_sqrt_two(m):
    assert abs(m.sqrt_by_fixed_point(2.0) - 1.4142135623730951) < 1e-10


def normal_sqrt_perfect_square(m):
    assert abs(m.sqrt_by_fixed_point(144.0) - 12.0) < 1e-9


def normal_converges_to_zero(m):
    assert abs(m.fixed_point(_halving, 1.0)) < 1e-9


def boundary_large(m):
    assert abs(m.sqrt_by_fixed_point(1000000.0) - 1000.0) < 1e-6


def boundary_fraction(m):
    assert abs(m.sqrt_by_fixed_point(0.25) - 0.5) < 1e-10


def edge_zero(m):
    assert abs(m.sqrt_by_fixed_point(0.0)) < 1e-15


def degenerate_negative(m):
    try:
        m.sqrt_by_fixed_point(-9.0)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for negative input')


TESTS = [
    {'id': 'normal_sqrt_two', 'kind': 'normal', 'fn': normal_sqrt_two},
    {'id': 'normal_sqrt_perfect_square', 'kind': 'normal', 'fn': normal_sqrt_perfect_square},
    {'id': 'normal_converges_to_zero', 'kind': 'normal', 'fn': normal_converges_to_zero},
    {'id': 'boundary_large', 'kind': 'boundary', 'fn': boundary_large},
    {'id': 'boundary_fraction', 'kind': 'boundary', 'fn': boundary_fraction},
    {'id': 'edge_zero', 'kind': 'edge', 'fn': edge_zero},
    {'id': 'degenerate_negative', 'kind': 'degenerate', 'fn': degenerate_negative},
]
