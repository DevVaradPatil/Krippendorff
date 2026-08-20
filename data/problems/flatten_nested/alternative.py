'''Flattening with an explicit stack instead of recursion.'''


def flatten(nested):
    '''Return every non-list item of a nested list, in order.'''
    result = []
    stack = list(nested)
    while stack:
        item = stack.pop(0)
        if isinstance(item, list):
            stack = list(item) + stack
        else:
            result.append(item)
    return result


def depth(nested):
    '''Return the nesting depth; a flat list is depth 1.'''
    if not isinstance(nested, list):
        return 0
    if len(nested) == 0:
        return 1
    return 1 + max(depth(item) for item in nested)
