'''Tests for matrix_transpose.

`edge_rows_are_independent` writes into one row of the result and then reads
another. That is the only way shared-row aliasing -- from `[[0] * rows] * cols`
or from a shallow row copy -- becomes visible; every value-equality check passes
happily with rows that are secretly the same object.
'''


def normal_rectangular(m):
    assert m.transpose([[1, 2, 3], [4, 5, 6]]) == [[1, 4], [2, 5], [3, 6]]


def normal_square(m):
    assert m.transpose([[1, 2], [3, 4]]) == [[1, 3], [2, 4]]


def boundary_single_row(m):
    assert m.transpose([[1, 2, 3]]) == [[1], [2], [3]]


def boundary_single_column(m):
    assert m.transpose([[1], [2], [3]]) == [[1, 2, 3]]


def edge_empty_matrix(m):
    assert m.transpose([]) == []


def edge_rows_are_independent(m):
    result = m.transpose([[1, 2], [3, 4]])
    result[0][0] = 99
    assert result[1] == [2, 4], 'writing one row changed another: ' + repr(result)


def edge_duplicate_rows_are_copies(m):
    original = [[1, 2], [3, 4]]
    copy = m.duplicate_rows(original)
    copy[0][0] = 99
    assert original[0] == [1, 2], 'the original was modified: ' + repr(original)


TESTS = [
    {'id': 'normal_rectangular', 'kind': 'normal', 'fn': normal_rectangular},
    {'id': 'normal_square', 'kind': 'normal', 'fn': normal_square},
    {'id': 'boundary_single_row', 'kind': 'boundary', 'fn': boundary_single_row},
    {'id': 'boundary_single_column', 'kind': 'boundary', 'fn': boundary_single_column},
    {'id': 'edge_empty_matrix', 'kind': 'edge', 'fn': edge_empty_matrix},
    {'id': 'edge_rows_are_independent', 'kind': 'edge', 'fn': edge_rows_are_independent},
    {'id': 'edge_duplicate_rows_are_copies', 'kind': 'edge', 'fn': edge_duplicate_rows_are_copies},
]
