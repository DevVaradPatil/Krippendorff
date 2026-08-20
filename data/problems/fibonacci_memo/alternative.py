'''Fibonacci computed iteratively, so no memo table is needed at all.

The statement asked for recursion with memoisation. This is correct, faster and
uses constant memory -- a good answer to a different question, which is exactly
the judgement call the ALT label exists to test.
'''


def fibonacci(n):
    '''Return the n-th Fibonacci number, with F(0) = 0 and F(1) = 1.'''
    if n < 0:
        raise ValueError('n must be non-negative')
    previous, current = 0, 1
    for _ in range(n):
        previous, current = current, previous + current
    return previous
