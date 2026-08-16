'''Primes by trial division rather than by sieving.

Slower and not the requested algorithm, but correct. Whether that should cost
marks is a rubric question, not a correctness one -- the ALT label is here to
check the grader does not silently treat "different" as "wrong".
'''


def _is_prime(k):
    if k < 2:
        return False
    d = 2
    while d * d <= k:
        if k % d == 0:
            return False
        d = d + 1
    return True


def primes_up_to(n):
    '''Return every prime <= n, in ascending order.'''
    return [k for k in range(2, n + 1) if _is_prime(k)]
