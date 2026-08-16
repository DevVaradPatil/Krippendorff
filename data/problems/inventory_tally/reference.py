'''Inventory tallying and restocking.'''


def tally(items, counts=None):
    '''Return a dict counting each non-blank item.'''
    if counts is None:
        counts = {}
    for item in items:
        name = item.strip()
        if name == '':
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts


def restock(inventory, additions):
    '''Return a new inventory with additions applied; inputs are unchanged.'''
    updated = inventory.copy()
    for name, quantity in additions.items():
        updated[name] = updated.get(name, 0) + quantity
    return updated


def total_units(inventory):
    '''Return the total number of units held.'''
    total = 0
    for quantity in inventory.values():
        total = total + quantity
    return total
