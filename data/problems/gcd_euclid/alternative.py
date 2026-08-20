'''Euclid's algorithm as a loop rather than a recursion.'''


def gcd(a, b):
    '''Return the greatest common divisor of two non-negative integers.'''
    if a < 0 or b < 0:
        raise ValueError('gcd is defined for non-negative integers')
    while b != 0:
        a, b = b, a % b
    return a


def lcm(a, b):
    '''Return the least common multiple, or 0 when either input is 0.'''
    if a == 0 or b == 0:
        return 0
    return a * b // gcd(a, b)
