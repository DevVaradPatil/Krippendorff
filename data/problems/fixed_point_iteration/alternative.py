'''Fixed-point iteration with the tolerance as the loop condition.'''


def fixed_point(g, x0, tol=1e-12, max_iter=200):
    '''Iterate x = g(x) until successive values settle within tol.'''
    x = x0
    following = g(x)
    steps = 1
    while abs(following - x) >= tol and steps < max_iter:
        x = following
        following = g(x)
        steps = steps + 1
    return following


def sqrt_by_fixed_point(a, tol=1e-12):
    '''Square root of a via the Babylonian map, as a fixed point.'''
    if a < 0:
        raise ValueError('the square root of a negative number is not real')
    if a == 0:
        return 0.0
    return fixed_point(lambda x: (x + a / x) / 2.0, a, tol)
