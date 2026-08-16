'''Tests for inventory_tally.

Three cases exist purely to expose state that outlives a call:
`edge_tally_calls_independent` for a mutable default argument,
`edge_total_units_repeatable` for an accumulator hoisted to module scope, and
`edge_restock_does_not_mutate` for a missing copy. All three pass trivially when
each function is called exactly once, which is why each calls twice or inspects
the caller's data afterwards.
'''


def normal_tally(m):
    assert m.tally(['nut', 'bolt', 'nut']) == {'nut': 2, 'bolt': 1}


def normal_blank_entries_skipped(m):
    assert m.tally(['nut', '  ', 'bolt', '']) == {'nut': 1, 'bolt': 1}


def normal_restock(m):
    assert m.restock({'nut': 2}, {'nut': 3, 'bolt': 1}) == {'nut': 5, 'bolt': 1}


def normal_total_units(m):
    assert m.total_units({'nut': 2, 'bolt': 3}) == 5


def edge_tally_calls_independent(m):
    first = m.tally(['nut'])
    second = m.tally(['nut'])
    assert first == {'nut': 1}
    assert second == {'nut': 1}, 'a second call returned ' + repr(second)


def edge_total_units_repeatable(m):
    assert m.total_units({'a': 4}) == 4
    assert m.total_units({'a': 4}) == 4, 'a second call disagreed with the first'


def edge_restock_does_not_mutate(m):
    inventory = {'nut': 2}
    m.restock(inventory, {'nut': 1})
    assert inventory == {'nut': 2}, 'the original inventory changed: ' + repr(inventory)


TESTS = [
    {'id': 'normal_tally', 'kind': 'normal', 'fn': normal_tally},
    {'id': 'normal_blank_entries_skipped', 'kind': 'normal', 'fn': normal_blank_entries_skipped},
    {'id': 'normal_restock', 'kind': 'normal', 'fn': normal_restock},
    {'id': 'normal_total_units', 'kind': 'normal', 'fn': normal_total_units},
    {'id': 'edge_tally_calls_independent', 'kind': 'edge', 'fn': edge_tally_calls_independent},
    {'id': 'edge_total_units_repeatable', 'kind': 'edge', 'fn': edge_total_units_repeatable},
    {'id': 'edge_restock_does_not_mutate', 'kind': 'edge', 'fn': edge_restock_does_not_mutate},
]
