'''Tests for list_dedupe.

Two cases here exist to catch bugs that are invisible to a single call:
`edge_calls_are_independent` calls dedupe twice, which is the only way a mutable
default argument shows itself, and `edge_inputs_not_modified` checks the
caller's list afterwards, which is the only way aliasing shows itself.
'''


def normal_dedupe(m):
    assert m.dedupe([1, 2, 2, 3, 1]) == [1, 2, 3]


def normal_preserves_order(m):
    assert m.dedupe(['c', 'a', 'c', 'b', 'a']) == ['c', 'a', 'b']


def edge_calls_are_independent(m):
    first = m.dedupe([1, 2, 3])
    second = m.dedupe([1, 2, 3])
    assert first == [1, 2, 3]
    assert second == [1, 2, 3], 'a second call returned ' + repr(second)


def normal_merged(m):
    assert m.merged_unique([1, 2], [2, 3, 3]) == [1, 2, 3]


def edge_inputs_not_modified(m):
    a = [1, 2]
    b = [3]
    m.merged_unique(a, b)
    assert a == [1, 2], 'first argument was modified: ' + repr(a)
    assert b == [3], 'second argument was modified: ' + repr(b)


def edge_empty(m):
    assert m.dedupe([]) == []
    assert m.merged_unique([], []) == []


TESTS = [
    {'id': 'normal_dedupe', 'kind': 'normal', 'fn': normal_dedupe},
    {'id': 'normal_preserves_order', 'kind': 'normal', 'fn': normal_preserves_order},
    {'id': 'normal_merged', 'kind': 'normal', 'fn': normal_merged},
    {'id': 'edge_calls_are_independent', 'kind': 'edge', 'fn': edge_calls_are_independent},
    {'id': 'edge_inputs_not_modified', 'kind': 'edge', 'fn': edge_inputs_not_modified},
    {'id': 'edge_empty', 'kind': 'edge', 'fn': edge_empty},
]
