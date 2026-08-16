'''Square root by Newton's method.'''


def newton_sqrt(x, tol=1e-12, max_iter=100):
    '''Return the square root of x, iterating until successive guesses settle.'''
    if x < 0:
        raise ValueError('the square root of a negative number is not real')
    if x == 0:
        return 0.0
    guess = x / 2.0
    for _ in range(max_iter):
        better = (guess + x / guess) / 2.0
        # Stop when the answer stops moving, not after a fixed count.
        if abs(better - guess) < tol:
            return better
        guess = better
    return guess
