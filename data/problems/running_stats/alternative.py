'''Mean and sample variance using built-ins instead of explicit accumulators.'''


def mean(values):
    '''Return the arithmetic mean of a non-empty sequence of numbers.'''
    if len(values) == 0:
        raise ValueError('mean of an empty sequence is undefined')
    return sum(values) / len(values)


def variance(values):
    '''Return the sample variance, dividing by n - 1 rather than by n.'''
    if len(values) < 2:
        raise ValueError('sample variance needs at least two values')
    mu = mean(values)
    return sum((value - mu) ** 2 for value in values) / (len(values) - 1)
