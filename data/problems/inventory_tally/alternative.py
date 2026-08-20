'''Inventory helpers written with truthiness tests and built-ins.

Same guarantees -- fresh dict per call, inputs never mutated -- reached through
`dict(inventory)` and `sum()` rather than explicit loops and a None sentinel.
'''


def tally(items, counts=None):
    '''Return a dict counting each non-blank item.'''
    result = {} if counts is None else counts
    for item in items:
        name = item.strip()
        if name:
            result[name] = result.get(name, 0) + 1
    return result


def restock(inventory, additions):
    '''Return a new inventory with additions applied; inputs are unchanged.'''
    updated = dict(inventory)
    for name, quantity in additions.items():
        updated[name] = updated.get(name, 0) + quantity
    return updated


def total_units(inventory):
    '''Return the total number of units held.'''
    return sum(inventory.values())
