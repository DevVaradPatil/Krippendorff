'''Mean and sample variance.'''


def mean(values):
    '''Return the arithmetic mean of a non-empty sequence of numbers.'''
    if len(values) == 0:
        raise ValueError('mean of an empty sequence is undefined')
    total = 0.0
    for value in values:
        total = total + value
    return total / len(values)


def variance(values):
    '''Return the sample variance, dividing by n - 1 rather than by n.'''
    if len(values) < 2:
        raise ValueError('sample variance needs at least two values')
    mu = mean(values)
    total = 0.0
    for value in values:
        total = total + (value - mu) ** 2
    # n - 1: the sample variance, not the population variance.
    return total / (len(values) - 1)
