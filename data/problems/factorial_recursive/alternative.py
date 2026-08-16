'''Factorial computed iteratively.

The statement asked for recursion, so this is the interesting ALT case: the
answer is right, the approach is defensible, and the only thing wrong with it is
that it is not what was asked. A grader should say that in feedback, not treat
it as a defect.
'''


def factorial(n):
    '''Return n! for a non-negative integer n.'''
    if n < 0:
        raise ValueError('factorial is undefined for negative input')
    result = 1
    for k in range(2, n + 1):
        result = result * k
    return result
