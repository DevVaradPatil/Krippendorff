'''Matrix multiplication.'''


def multiply(a, b):
    '''Return the matrix product of a and b.'''
    if len(a) == 0 or len(b) == 0:
        return []
    if len(a[0]) != len(b):
        raise ValueError('inner dimensions must match')
    rows = len(a)
    cols = len(b[0])
    inner = len(b)
    # One list per row: [[0] * cols] * rows would share a single row object.
    result = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        for j in range(cols):
            total = 0
            for k in range(inner):
                total = total + a[i][k] * b[k][j]
            result[i][j] = total
    return result
