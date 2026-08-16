'''Tests for sieve_primes.

`boundary_perfect_square` exists because the sqrt bound is the classic
off-by-one site: with `int(n ** 0.5)` instead of `+ 1`, 25 survives the sieve
and is reported as prime, and nothing else in the suite would notice.
'''


def normal_small(m):
    assert m.primes_up_to(10) == [2, 3, 5, 7]


def normal_thirty(m):
    assert m.primes_up_to(30) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]


def boundary_perfect_square(m):
    assert m.primes_up_to(25) == [2, 3, 5, 7, 11, 13, 17, 19, 23]


def boundary_includes_n(m):
    assert m.primes_up_to(7) == [2, 3, 5, 7]


def edge_two(m):
    assert m.primes_up_to(2) == [2]


def edge_below_two(m):
    assert m.primes_up_to(1) == []


def degenerate_zero_and_negative(m):
    assert m.primes_up_to(0) == []
    assert m.primes_up_to(-5) == []


TESTS = [
    {'id': 'normal_small', 'kind': 'normal', 'fn': normal_small},
    {'id': 'normal_thirty', 'kind': 'normal', 'fn': normal_thirty},
    {'id': 'boundary_perfect_square', 'kind': 'boundary', 'fn': boundary_perfect_square},
    {'id': 'boundary_includes_n', 'kind': 'boundary', 'fn': boundary_includes_n},
    {'id': 'edge_two', 'kind': 'edge', 'fn': edge_two},
    {'id': 'edge_below_two', 'kind': 'edge', 'fn': edge_below_two},
    {'id': 'degenerate_zero_and_negative', 'kind': 'degenerate', 'fn': degenerate_zero_and_negative},
]
