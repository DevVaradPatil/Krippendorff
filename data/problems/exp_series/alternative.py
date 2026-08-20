'''The exponential series with each term built from a running factorial.

The reference derives each term from the previous one. This tracks the power and
the factorial separately, which is clearer to read and costs one more multiply.
'''


def exp_series(x, tol=1e-12, max_terms=100):
    '''Approximate e**x by summing Taylor terms until they fall below tol.'''
    total = 0.0
    factorial = 1.0
    power = 1.0
    for k in range(max_terms):
        if k > 0:
            factorial = factorial * k
            power = power * x
        term = power / factorial
        total = total + term
        if abs(term) < tol:
            return total
    return total
