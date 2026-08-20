'''Matrix product built from zip and a generator expression.

Transposing b once up front turns the inner loop into a dot product over paired
rows, which is the same arithmetic in a quarter of the lines.
'''


def multiply(a, b):
    '''Return the matrix product of a and b.'''
    if len(a) == 0 or len(b) == 0:
        return []
    if len(a[0]) != len(b):
        raise ValueError('inner dimensions must match')
    columns = list(zip(*b))
    return [
        [sum(x * y for x, y in zip(row, column)) for column in columns]
        for row in a
    ]
