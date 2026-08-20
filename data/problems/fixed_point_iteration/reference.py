'''Fixed-point iteration.'''


def fixed_point(g, x0, tol=1e-12, max_iter=200):
    '''Iterate x = g(x) until successive values settle within tol.'''
    x = x0
    for _ in range(max_iter):
        following = g(x)
        # Stop on movement, not after a fixed number of steps.
        if abs(following - x) < tol:
            return following
        x = following
    return x


def sqrt_by_fixed_point(a, tol=1e-12):
    '''Square root of a via the Babylonian map, as a fixed point.'''
    if a < 0:
        raise ValueError('the square root of a negative number is not real')
    if a == 0:
        return 0.0
    return fixed_point(lambda x: (x + a / x) / 2.0, a, tol)
