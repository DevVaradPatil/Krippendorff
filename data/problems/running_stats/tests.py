'''Tests for running_stats.

`normal_mean_of_integers` uses values whose mean is not an integer, so `//` in
place of `/` changes the answer -- with a mean that lands exactly on an integer,
integer division is invisible. `normal_sample_variance` distinguishes the n - 1
denominator from n, which is the off-by-one that matters here.

`edge_repeated_calls` catches an accumulator hoisted to module scope: the second
call inherits the first call's total.
'''


def normal_mean_of_integers(m):
    assert abs(m.mean([1, 2, 3, 4]) - 2.5) < 1e-12


def normal_mean_of_floats(m):
    assert abs(m.mean([0.5, 1.5, 2.5]) - 1.5) < 1e-12


def normal_sample_variance(m):
    # Sum of squared deviations is 5.0; sample variance divides by 4, not 5.
    assert abs(m.variance([2, 4, 4, 4, 5, 5, 7, 9]) - 4.571428571428571) < 1e-9


def boundary_two_values(m):
    assert abs(m.variance([1.0, 3.0]) - 2.0) < 1e-12


def edge_repeated_calls(m):
    first = m.mean([1.0, 2.0, 3.0])
    second = m.mean([1.0, 2.0, 3.0])
    assert abs(first - 2.0) < 1e-12
    assert abs(second - 2.0) < 1e-12, 'a second call returned ' + repr(second)


def degenerate_empty_mean(m):
    try:
        m.mean([])
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for an empty sequence')


def degenerate_single_variance(m):
    try:
        m.variance([4.0])
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for a single value')


TESTS = [
    {'id': 'normal_mean_of_integers', 'kind': 'normal', 'fn': normal_mean_of_integers},
    {'id': 'normal_mean_of_floats', 'kind': 'normal', 'fn': normal_mean_of_floats},
    {'id': 'normal_sample_variance', 'kind': 'normal', 'fn': normal_sample_variance},
    {'id': 'boundary_two_values', 'kind': 'boundary', 'fn': boundary_two_values},
    {'id': 'edge_repeated_calls', 'kind': 'edge', 'fn': edge_repeated_calls},
    {'id': 'degenerate_empty_mean', 'kind': 'degenerate', 'fn': degenerate_empty_mean},
    {'id': 'degenerate_single_variance', 'kind': 'degenerate', 'fn': degenerate_single_variance},
]
