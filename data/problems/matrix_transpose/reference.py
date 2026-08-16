'''Matrix transpose and independent row copies.'''


def transpose(matrix):
    '''Return a new matrix whose rows are the columns of the input.'''
    if len(matrix) == 0:
        return []
    rows = len(matrix)
    cols = len(matrix[0])
    # A comprehension per row: [[0] * rows] * cols would make every row the
    # same list object.
    result = [[0] * rows for _ in range(cols)]
    for i in range(rows):
        for j in range(cols):
            result[j][i] = matrix[i][j]
    return result


def duplicate_rows(matrix):
    '''Return a copy of the matrix in which each row is an independent list.'''
    return [row.copy() for row in matrix]
