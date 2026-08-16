'''Memoised recursive Fibonacci.'''


def fibonacci(n, memo=None):
    '''Return the n-th Fibonacci number, with F(0) = 0 and F(1) = 1.'''
    if n < 0:
        raise ValueError('n must be non-negative')
    if memo is None:
        memo = {}
    # Two base cases, and the recursion terminates only if both are present.
    if n == 0:
        return 0
    if n == 1:
        return 1
    if n in memo:
        return memo[n]
    memo[n] = fibonacci(n - 1, memo) + fibonacci(n - 2, memo)
    return memo[n]
