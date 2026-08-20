'''Recursive exponentiation and digit summing.'''


def power(base, exponent):
    '''Return base ** exponent for a non-negative integer exponent.'''
    if exponent < 0:
        raise ValueError('exponent must be non-negative')
    # Base case: anything to the zero is one.
    if exponent == 0:
        return 1
    half = power(base, exponent // 2)
    if exponent % 2 == 0:
        return half * half
    return half * half * base


def sum_digits(n):
    '''Return the sum of the decimal digits of a non-negative integer.'''
    if n < 0:
        raise ValueError('n must be non-negative')
    # Base case: a single digit is its own sum.
    if n < 10:
        return n
    return n % 10 + sum_digits(n // 10)
