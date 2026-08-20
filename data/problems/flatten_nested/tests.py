'''Tests for flatten_nested.

Both base cases get their own case: edge_not_a_list for the non-list bottom, and
edge_empty_list for the empty-list bottom. Deleting either sends the recursion
past the end of the structure rather than returning a wrong value, so these fail
by timeout, which is the honest signature of a missing base case.
'''


def normal_two_levels(m):
    assert m.flatten([1, [2, 3], 4]) == [1, 2, 3, 4]


def normal_deeply_nested(m):
    assert m.flatten([1, [2, [3, [4]]]]) == [1, 2, 3, 4]


def normal_depth_flat(m):
    assert m.depth([1, 2, 3]) == 1


def normal_depth_nested(m):
    assert m.depth([1, [2, [3]]]) == 3


def edge_not_a_list(m):
    assert m.depth(7) == 0


def edge_empty_list(m):
    assert m.flatten([]) == []
    assert m.depth([]) == 1


def edge_only_nesting(m):
    assert m.flatten([[], [[]]]) == []


TESTS = [
    {'id': 'normal_two_levels', 'kind': 'normal', 'fn': normal_two_levels},
    {'id': 'normal_deeply_nested', 'kind': 'normal', 'fn': normal_deeply_nested},
    {'id': 'normal_depth_flat', 'kind': 'normal', 'fn': normal_depth_flat},
    {'id': 'normal_depth_nested', 'kind': 'normal', 'fn': normal_depth_nested},
    {'id': 'edge_not_a_list', 'kind': 'edge', 'fn': edge_not_a_list},
    {'id': 'edge_empty_list', 'kind': 'edge', 'fn': edge_empty_list},
    {'id': 'edge_only_nesting', 'kind': 'edge', 'fn': edge_only_nesting},
]
