'''Tests for gcd_euclid.

`edge_b_is_zero` hits the base case directly, and `normal_coprime` forces the
recursion all the way down to it; a deleted base case recurses forever and is
caught by the per-case timeout rather than by a wrong answer.
'''


def normal_common_factor(m):
    assert m.gcd(48, 18) == 6


def normal_coprime(m):
    assert m.gcd(17, 5) == 1


def normal_lcm(m):
    assert m.lcm(4, 6) == 12


def edge_b_is_zero(m):
    assert m.gcd(9, 0) == 9


def edge_a_is_zero(m):
    assert m.gcd(0, 9) == 9


def edge_lcm_with_zero(m):
    assert m.lcm(0, 5) == 0


def degenerate_negative(m):
    try:
        m.gcd(-4, 2)
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for negative input')


TESTS = [
    {'id': 'normal_common_factor', 'kind': 'normal', 'fn': normal_common_factor},
    {'id': 'normal_coprime', 'kind': 'normal', 'fn': normal_coprime},
    {'id': 'normal_lcm', 'kind': 'normal', 'fn': normal_lcm},
    {'id': 'edge_b_is_zero', 'kind': 'edge', 'fn': edge_b_is_zero},
    {'id': 'edge_a_is_zero', 'kind': 'edge', 'fn': edge_a_is_zero},
    {'id': 'edge_lcm_with_zero', 'kind': 'edge', 'fn': edge_lcm_with_zero},
    {'id': 'degenerate_negative', 'kind': 'degenerate', 'fn': degenerate_negative},
]
