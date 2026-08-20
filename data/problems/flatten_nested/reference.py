'''Flattening arbitrarily nested lists.'''


def flatten(nested):
    '''Return every non-list item of a nested list, in order.'''
    result = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def depth(nested):
    '''Return the nesting depth; a flat list is depth 1.'''
    # Base case: anything that is not a list bottoms out at zero.
    if not isinstance(nested, list):
        return 0
    # Base case: an empty list has no children to recurse into.
    if len(nested) == 0:
        return 1
    deepest = 0
    for item in nested:
        if depth(item) > deepest:
            deepest = depth(item)
    return 1 + deepest
