'''Factorial, computed recursively.'''


def factorial(n):
    '''Return n! for a non-negative integer n.'''
    if n < 0:
        raise ValueError('factorial is undefined for negative input')
    # Base case: without this the recursion never terminates.
    if n == 0:
        return 1
    return n * factorial(n - 1)
