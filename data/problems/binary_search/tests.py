'''Tests for binary_search.

The first and last elements each get their own case. Both are where an
inclusive/exclusive mix-up in the initial bounds shows up, and a suite that only
searches for middle elements passes happily with either convention.
'''


def normal_middle(m):
    assert m.binary_search([1, 3, 5, 7, 9], 5) == 2


def normal_absent(m):
    assert m.binary_search([1, 3, 5, 7, 9], 4) == -1


def boundary_first_element(m):
    assert m.binary_search([1, 3, 5, 7, 9], 1) == 0


def boundary_last_element(m):
    assert m.binary_search([1, 3, 5, 7, 9], 9) == 4


def boundary_even_length(m):
    assert m.binary_search([2, 4, 6, 8], 8) == 3


def edge_single_item(m):
    assert m.binary_search([42], 42) == 0
    assert m.binary_search([42], 7) == -1


def edge_empty(m):
    assert m.binary_search([], 1) == -1


TESTS = [
    {'id': 'normal_middle', 'kind': 'normal', 'fn': normal_middle},
    {'id': 'normal_absent', 'kind': 'normal', 'fn': normal_absent},
    {'id': 'boundary_first_element', 'kind': 'boundary', 'fn': boundary_first_element},
    {'id': 'boundary_last_element', 'kind': 'boundary', 'fn': boundary_last_element},
    {'id': 'boundary_even_length', 'kind': 'boundary', 'fn': boundary_even_length},
    {'id': 'edge_single_item', 'kind': 'edge', 'fn': edge_single_item},
    {'id': 'edge_empty', 'kind': 'edge', 'fn': edge_empty},
]
