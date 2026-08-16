'''Tests for matrix_multiply.

The three nested loops are three separate off-by-one sites, and they fail
differently: a short row loop drops a row, a short column loop drops a column,
and a short inner loop leaves every entry subtly wrong while the shape stays
correct. `normal_rectangular` and `normal_inner_sum` between them catch all three.
'''


def normal_square(m):
    assert m.multiply([[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [[19, 22], [43, 50]]


def normal_rectangular(m):
    assert m.multiply([[1, 2, 3], [4, 5, 6]], [[7, 8], [9, 10], [11, 12]]) == [
        [58, 64],
        [139, 154],
    ]


def normal_inner_sum(m):
    assert m.multiply([[1, 1, 1]], [[2], [3], [4]]) == [[9]]


def normal_identity(m):
    assert m.multiply([[3, 5], [7, 9]], [[1, 0], [0, 1]]) == [[3, 5], [7, 9]]


def edge_rows_are_independent(m):
    result = m.multiply([[1, 0], [0, 1]], [[1, 2], [3, 4]])
    result[0][0] = 99
    assert result[1] == [3, 4], 'writing one row changed another: ' + repr(result)


def edge_empty(m):
    assert m.multiply([], []) == []


def degenerate_dimension_mismatch(m):
    try:
        m.multiply([[1, 2, 3]], [[1, 2]])
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for mismatched inner dimensions')


TESTS = [
    {'id': 'normal_square', 'kind': 'normal', 'fn': normal_square},
    {'id': 'normal_rectangular', 'kind': 'normal', 'fn': normal_rectangular},
    {'id': 'normal_inner_sum', 'kind': 'normal', 'fn': normal_inner_sum},
    {'id': 'normal_identity', 'kind': 'normal', 'fn': normal_identity},
    {'id': 'edge_rows_are_independent', 'kind': 'edge', 'fn': edge_rows_are_independent},
    {'id': 'edge_empty', 'kind': 'edge', 'fn': edge_empty},
    {'id': 'degenerate_dimension_mismatch', 'kind': 'degenerate', 'fn': degenerate_dimension_mismatch},
]
