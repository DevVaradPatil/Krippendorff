'''The same cart using dict() copies and comprehensions.'''


def add_items(names, cart=None):
    '''Count each name into a cart, starting a fresh one when none is given.'''
    result = {} if cart is None else cart
    for name in names:
        result[name] = result.get(name, 0) + 1
    return result


def collect_problems(quantities, problems=None):
    '''Return the quantities that are not strictly positive.'''
    found = [] if problems is None else problems
    found.extend(quantity for quantity in quantities if quantity <= 0)
    return found


def snapshot(cart):
    '''Return an independent copy of the cart.'''
    return dict(cart)


def merge_carts(first, second):
    '''Return a new cart holding both, leaving the inputs untouched.'''
    merged = dict(first)
    for name, quantity in second.items():
        merged[name] = merged.get(name, 0) + quantity
    return merged
