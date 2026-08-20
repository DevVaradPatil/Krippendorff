'''Newton's method with the convergence test as the loop condition.'''


def newton_sqrt(x, tol=1e-12, max_iter=100):
    '''Return the square root of x, iterating until successive guesses settle.'''
    if x < 0:
        raise ValueError('the square root of a negative number is not real')
    if x == 0:
        return 0.0
    guess = x
    step = 0
    while step < max_iter:
        better = 0.5 * (guess + x / guess)
        if abs(better - guess) < tol:
            return better
        guess = better
        step = step + 1
    return guess
