'''Tests for recursive_math.

Each function gets a case that lands exactly on its base case (power to the
zero, a single-digit sum) and one that has to recurse down to it. A deleted base
case then runs away rather than returning something subtly wrong.
'''


def normal_power(m):
    assert m.power(2, 10) == 1024


def normal_power_odd_exponent(m):
    assert m.power(3, 5) == 243


def normal_sum_digits(m):
    assert m.sum_digits(9425) == 20


def edge_power_zero(m):
    assert m.power(7, 0) == 1


def edge_power_one(m):
    assert m.power(7, 1) == 7


def edge_single_digit(m):
    assert m.sum_digits(0) == 0
    assert m.sum_digits(7) == 7


def boundary_large_power(m):
    assert m.power(2, 40) == 1099511627776


def degenerate_negative_exponent(m):
    try:
        m.power(2, -1)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for a negative exponent')


TESTS = [
    {'id': 'normal_power', 'kind': 'normal', 'fn': normal_power},
    {'id': 'normal_power_odd_exponent', 'kind': 'normal', 'fn': normal_power_odd_exponent},
    {'id': 'normal_sum_digits', 'kind': 'normal', 'fn': normal_sum_digits},
    {'id': 'edge_power_zero', 'kind': 'edge', 'fn': edge_power_zero},
    {'id': 'edge_power_one', 'kind': 'edge', 'fn': edge_power_one},
    {'id': 'edge_single_digit', 'kind': 'edge', 'fn': edge_single_digit},
    {'id': 'boundary_large_power', 'kind': 'boundary', 'fn': boundary_large_power},
    {'id': 'degenerate_negative_exponent', 'kind': 'degenerate', 'fn': degenerate_negative_exponent},
]
