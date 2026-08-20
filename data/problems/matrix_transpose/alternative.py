'''Transpose by unpacking the rows into zip.

`zip(*matrix)` is the standard Python idiom for this; each column comes back as
a tuple, so it is copied into a list to match the requested return type.
'''


def transpose(matrix):
    '''Return a new matrix whose rows are the columns of the input.'''
    return [list(column) for column in zip(*matrix)]


def duplicate_rows(matrix):
    '''Return a copy of the matrix in which each row is an independent list.'''
    return [list(row) for row in matrix]
