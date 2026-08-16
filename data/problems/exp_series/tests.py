'''Tests for exp_series.

`normal_e_to_the_one` is tight to 1e-10, which a fixed three-term sum cannot
reach. `normal_larger_x` needs many terms before they shrink, so it separates a
genuine convergence test from a loop that simply runs out of iterations.
'''


def normal_e_to_the_one(m):
    assert abs(m.exp_series(1.0) - 2.718281828459045) < 1e-10


def normal_zero(m):
    assert abs(m.exp_series(0.0) - 1.0) < 1e-12


def normal_larger_x(m):
    assert abs(m.exp_series(5.0) - 148.4131591025766) < 1e-8


def normal_negative_x(m):
    assert abs(m.exp_series(-1.0) - 0.36787944117144233) < 1e-10


def boundary_small_x(m):
    assert abs(m.exp_series(1e-6) - 1.0000010000005) < 1e-9


def edge_loose_tolerance(m):
    assert abs(m.exp_series(1.0, 1e-3) - 2.718281828459045) < 1e-2


TESTS = [
    {'id': 'normal_e_to_the_one', 'kind': 'normal', 'fn': normal_e_to_the_one},
    {'id': 'normal_zero', 'kind': 'normal', 'fn': normal_zero},
    {'id': 'normal_larger_x', 'kind': 'normal', 'fn': normal_larger_x},
    {'id': 'normal_negative_x', 'kind': 'normal', 'fn': normal_negative_x},
    {'id': 'boundary_small_x', 'kind': 'boundary', 'fn': boundary_small_x},
    {'id': 'edge_loose_tolerance', 'kind': 'edge', 'fn': edge_loose_tolerance},
]
