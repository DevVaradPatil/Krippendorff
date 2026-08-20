'''Tests for shopping_cart.

Four cases here exist only to expose state that outlives a call: two call the
same function twice, which is the only way a mutable default argument shows
itself, and two inspect the caller's dictionary afterwards, which is the only
way a missing copy does.
'''


def normal_add_items(m):
    assert m.add_items(['apple', 'pear', 'apple']) == {'apple': 2, 'pear': 1}


def normal_collect_problems(m):
    assert m.collect_problems([3, 0, 5, -2]) == [0, -2]


def normal_merge(m):
    assert m.merge_carts({'apple': 1}, {'apple': 2, 'fig': 1}) == {'apple': 3, 'fig': 1}


def edge_add_items_calls_are_independent(m):
    first = m.add_items(['apple'])
    second = m.add_items(['apple'])
    assert first == {'apple': 1}
    assert second == {'apple': 1}, 'a second call returned ' + repr(second)


def edge_collect_problems_calls_are_independent(m):
    first = m.collect_problems([-1])
    second = m.collect_problems([-1])
    assert first == [-1]
    assert second == [-1], 'a second call returned ' + repr(second)


def edge_snapshot_is_independent(m):
    cart = {'apple': 1}
    copy = m.snapshot(cart)
    copy['apple'] = 99
    assert cart == {'apple': 1}, 'the original changed: ' + repr(cart)


def edge_merge_does_not_mutate(m):
    first = {'apple': 1}
    second = {'fig': 1}
    m.merge_carts(first, second)
    assert first == {'apple': 1}, 'the first input changed: ' + repr(first)
    assert second == {'fig': 1}, 'the second input changed: ' + repr(second)


def edge_empty_inputs(m):
    assert m.add_items([]) == {}
    assert m.collect_problems([]) == []


TESTS = [
    {'id': 'normal_add_items', 'kind': 'normal', 'fn': normal_add_items},
    {'id': 'normal_collect_problems', 'kind': 'normal', 'fn': normal_collect_problems},
    {'id': 'normal_merge', 'kind': 'normal', 'fn': normal_merge},
    {'id': 'edge_add_items_calls_are_independent', 'kind': 'edge', 'fn': edge_add_items_calls_are_independent},
    {'id': 'edge_collect_problems_calls_are_independent', 'kind': 'edge', 'fn': edge_collect_problems_calls_are_independent},
    {'id': 'edge_snapshot_is_independent', 'kind': 'edge', 'fn': edge_snapshot_is_independent},
    {'id': 'edge_merge_does_not_mutate', 'kind': 'edge', 'fn': edge_merge_does_not_mutate},
    {'id': 'edge_empty_inputs', 'kind': 'edge', 'fn': edge_empty_inputs},
]
