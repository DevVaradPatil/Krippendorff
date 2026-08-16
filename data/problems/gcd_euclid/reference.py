'''Greatest common divisor and least common multiple.'''


def gcd(a, b):
    '''Return the greatest common divisor of two non-negative integers.'''
    if a < 0 or b < 0:
        raise ValueError('gcd is defined for non-negative integers')
    # Base case: a remainder of zero means the divisor is the answer.
    if b == 0:
        return a
    return gcd(b, a % b)


def lcm(a, b):
    '''Return the least common multiple, or 0 when either input is 0.'''
    if a == 0 or b == 0:
        return 0
    # Integer division: the product is always divisible by the gcd.
    return a * b // gcd(a, b)
