'''Tests for fibonacci_memo.

`boundary_large_n` is the memoisation test: without a cache the naive recursion
for n = 32 takes long enough to hit the per-case timeout, so it also catches a
solution that memoises into a structure it never reads.
'''


def normal_small(m):
    assert m.fibonacci(10) == 55


def normal_sequence(m):
    assert [m.fibonacci(k) for k in range(8)] == [0, 1, 1, 2, 3, 5, 8, 13]


def edge_zero(m):
    assert m.fibonacci(0) == 0


def edge_one(m):
    assert m.fibonacci(1) == 1


def boundary_large_n(m):
    assert m.fibonacci(32) == 2178309


def edge_repeated_calls(m):
    assert m.fibonacci(12) == 144
    assert m.fibonacci(12) == 144, 'a second call disagreed with the first'


def degenerate_negative(m):
    try:
        m.fibonacci(-1)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for negative input')


TESTS = [
    {'id': 'normal_small', 'kind': 'normal', 'fn': normal_small},
    {'id': 'normal_sequence', 'kind': 'normal', 'fn': normal_sequence},
    {'id': 'edge_zero', 'kind': 'edge', 'fn': edge_zero},
    {'id': 'edge_one', 'kind': 'edge', 'fn': edge_one},
    {'id': 'boundary_large_n', 'kind': 'boundary', 'fn': boundary_large_n},
    {'id': 'edge_repeated_calls', 'kind': 'edge', 'fn': edge_repeated_calls},
    {'id': 'degenerate_negative', 'kind': 'degenerate', 'fn': degenerate_negative},
]
