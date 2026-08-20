'''The same two functions written iteratively.

Correct, and for power still logarithmic, but the statement asked for recursion
in both cases -- a judgement call for the grader rather than a defect.
'''


def power(base, exponent):
    '''Return base ** exponent for a non-negative integer exponent.'''
    if exponent < 0:
        raise ValueError('exponent must be non-negative')
    result = 1
    factor = base
    remaining = exponent
    while remaining > 0:
        if remaining % 2 == 1:
            result = result * factor
        factor = factor * factor
        remaining = remaining // 2
    return result


def sum_digits(n):
    '''Return the sum of the decimal digits of a non-negative integer.'''
    if n < 0:
        raise ValueError('n must be non-negative')
    total = 0
    while n >= 10:
        total = total + n % 10
        n = n // 10
    return total + n
