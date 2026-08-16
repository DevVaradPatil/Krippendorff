'''Composite trapezoidal rule for definite integrals.'''


def trapezoid(f, a, b, n):
    '''Approximate the integral of f from a to b using n trapezoids.'''
    if n <= 0:
        raise ValueError('n must be a positive integer')
    # Width of one subinterval; the whole method hangs on this being a float.
    h = (b - a) / n
    total = 0.0
    total = total + f(a) / 2.0
    total = total + f(b) / 2.0
    for i in range(1, n):
        total = total + f(a + i * h)
    return total * h
