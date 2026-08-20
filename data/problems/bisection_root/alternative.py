'''Bisection driven by a while loop on the bracket width.

The reference loops a fixed number of times and returns early once the bracket
is narrow; this makes the tolerance the loop condition instead.
'''


def bisect(f, lo, hi, tol=1e-10, max_iter=200):
    '''Return a root of f in [lo, hi], bisecting until the bracket is under tol.'''
    if f(lo) * f(hi) > 0:
        raise ValueError('f(lo) and f(hi) must have opposite signs')
    steps = 0
    while hi - lo >= tol and steps < max_iter:
        mid = (lo + hi) / 2.0
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
        steps = steps + 1
    return (lo + hi) / 2.0
