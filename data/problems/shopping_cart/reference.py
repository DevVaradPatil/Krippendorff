'''A shopping cart built from plain dictionaries.'''


def add_items(names, cart=None):
    '''Count each name into a cart, starting a fresh one when none is given.'''
    # None, not {}: a mutable default is built once and would leak between calls.
    if cart is None:
        cart = {}
    for name in names:
        cart[name] = cart.get(name, 0) + 1
    return cart


def collect_problems(quantities, problems=None):
    '''Return the quantities that are not strictly positive.'''
    if problems is None:
        problems = []
    for quantity in quantities:
        if quantity > 0:
            continue
        problems.append(quantity)
    return problems


def snapshot(cart):
    '''Return an independent copy of the cart.'''
    return cart.copy()


def merge_carts(first, second):
    '''Return a new cart holding both, leaving the inputs untouched.'''
    merged = first.copy()
    for name, quantity in second.items():
        merged[name] = merged.get(name, 0) + quantity
    return merged
