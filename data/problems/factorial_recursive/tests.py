'''Tests for factorial_recursive.

`edge_zero` carries the weight here: 0! = 1 is the base case, and a solution
that recurses on `n <= 1` without handling 0 separately either loops forever or
returns the wrong value for exactly this input.
'''


def normal_five(m):
    assert m.factorial(5) == 120


def normal_ten(m):
    assert m.factorial(10) == 3628800


def edge_zero(m):
    assert m.factorial(0) == 1


def edge_one(m):
    assert m.factorial(1) == 1


def boundary_deep(m):
    assert m.factorial(60) == 8320987112741390144276341183223364380754172606361245952449277696409600000000000000


def degenerate_negative(m):
    try:
        m.factorial(-3)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for negative input')


TESTS = [
    {'id': 'normal_five', 'kind': 'normal', 'fn': normal_five},
    {'id': 'normal_ten', 'kind': 'normal', 'fn': normal_ten},
    {'id': 'edge_zero', 'kind': 'edge', 'fn': edge_zero},
    {'id': 'edge_one', 'kind': 'edge', 'fn': edge_one},
    {'id': 'boundary_deep', 'kind': 'boundary', 'fn': boundary_deep},
    {'id': 'degenerate_negative', 'kind': 'degenerate', 'fn': degenerate_negative},
]
