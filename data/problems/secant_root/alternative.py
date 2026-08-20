'''The secant method written as a while loop over the last two estimates.'''


def secant(f, x0, x1, tol=1e-12, max_iter=100):
    '''Return a root of f, starting from the two points x0 and x1.'''
    if x0 == x1:
        raise ValueError('the two starting points must differ')
    steps = 0
    moved = tol + 1.0
    while moved >= tol and steps < max_iter:
        f0 = f(x0)
        f1 = f(x1)
        if abs(f1 - f0) < 1e-300:
            return x1
        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        moved = abs(x2 - x1)
        x0 = x1
        x1 = x2
        steps = steps + 1
    return x1
