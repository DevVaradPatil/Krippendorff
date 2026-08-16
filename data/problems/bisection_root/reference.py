'''Root finding by bisection.'''


def bisect(f, lo, hi, tol=1e-10, max_iter=200):
    '''Return a root of f in [lo, hi], bisecting until the bracket is under tol.'''
    if f(lo) * f(hi) > 0:
        raise ValueError('f(lo) and f(hi) must have opposite signs')
    for _ in range(max_iter):
        # Stop on the tolerance, not on a fixed iteration count.
        if hi - lo < tol:
            return (lo + hi) / 2.0
        mid = (lo + hi) / 2.0
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0
