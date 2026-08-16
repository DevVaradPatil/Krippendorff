'''Sieve of Eratosthenes.'''


def primes_up_to(n):
    '''Return every prime <= n, in ascending order.'''
    if n < 2:
        return []
    is_prime = [True] * (n + 1)
    is_prime[0] = False
    is_prime[1] = False
    # Crossing out multiples only needs to reach sqrt(n): any composite has a
    # factor at or below its square root.
    limit = int(n ** 0.5) + 1
    for p in range(2, limit):
        if is_prime[p]:
            for multiple in range(p * p, n + 1, p):
                is_prime[multiple] = False
    return [i for i in range(2, n + 1) if is_prime[i]]
