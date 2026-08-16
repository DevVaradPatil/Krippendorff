'''Tests for newton_sqrt.

Newton's method converges so fast that a loose tolerance hides a broken
stopping rule -- three iterations already look about right. `normal_two_tight`
and `boundary_large` are tight enough that a fixed small iteration count fails
while a genuine convergence check passes.
'''


def normal_two_tight(m):
    assert abs(m.newton_sqrt(2.0) - 1.4142135623730951) < 1e-10


def normal_perfect_square(m):
    assert abs(m.newton_sqrt(144.0) - 12.0) < 1e-9


def normal_fraction(m):
    assert abs(m.newton_sqrt(0.25) - 0.5) < 1e-10


def boundary_large(m):
    assert abs(m.newton_sqrt(1.0e6) - 1000.0) < 1e-6


def edge_zero(m):
    assert abs(m.newton_sqrt(0.0) - 0.0) < 1e-15


def edge_one(m):
    assert abs(m.newton_sqrt(1.0) - 1.0) < 1e-12


def degenerate_negative(m):
    try:
        m.newton_sqrt(-4.0)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for negative input')


TESTS = [
    {'id': 'normal_two_tight', 'kind': 'normal', 'fn': normal_two_tight},
    {'id': 'normal_perfect_square', 'kind': 'normal', 'fn': normal_perfect_square},
    {'id': 'normal_fraction', 'kind': 'normal', 'fn': normal_fraction},
    {'id': 'boundary_large', 'kind': 'boundary', 'fn': boundary_large},
    {'id': 'edge_zero', 'kind': 'edge', 'fn': edge_zero},
    {'id': 'edge_one', 'kind': 'edge', 'fn': edge_one},
    {'id': 'degenerate_negative', 'kind': 'degenerate', 'fn': degenerate_negative},
]
