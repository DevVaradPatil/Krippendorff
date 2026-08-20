'''Root finding by the secant method.'''


def secant(f, x0, x1, tol=1e-12, max_iter=100):
    '''Return a root of f, starting from the two points x0 and x1.'''
    if x0 == x1:
        raise ValueError('the two starting points must differ')
    for _ in range(max_iter):
        f0 = f(x0)
        f1 = f(x1)
        if abs(f1 - f0) < 1e-300:
            return x1
        step = f1 * (x1 - x0) / (f1 - f0)
        x2 = x1 - step
        # Stop when the estimate settles, not after a set number of steps.
        if abs(x2 - x1) < tol:
            return x2
        x0 = x1
        x1 = x2
    return x1
