'''Trapezoidal rule, written as an averaged-endpoints sum.

Correct by a different route: instead of half-weighting the two endpoints, this
sums the average height of each individual trapezoid. Same answer, and a grader
that penalises it for not matching the reference shape is producing exactly the
false positive the ALT label exists to catch.
'''


def trapezoid(f, a, b, n):
    '''Approximate the integral of f from a to b using n trapezoids.'''
    if n <= 0:
        raise ValueError('n must be a positive integer')
    h = (b - a) / n
    xs = [a + i * h for i in range(n + 1)]
    return sum((f(xs[i]) + f(xs[i + 1])) / 2.0 * h for i in range(n))
