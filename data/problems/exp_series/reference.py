'''The exponential function by Taylor series.'''


def exp_series(x, tol=1e-12, max_terms=100):
    '''Approximate e**x by summing Taylor terms until they fall below tol.'''
    total = 0.0
    term = 1.0
    for k in range(max_terms):
        total = total + term
        # Stop on the size of the term, not after a fixed number of them.
        if abs(term) < tol:
            return total
        # Each term is the previous one times x / (k + 1).
        term = term * x / (k + 1)
    return total
