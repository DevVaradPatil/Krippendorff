'''Binary search expressed recursively rather than with a loop.

Same halving strategy, same complexity; the bounds live in the call stack
instead of in two mutable locals.
'''


def _search(items, target, lo, hi):
    if lo > hi:
        return -1
    mid = (lo + hi) // 2
    if items[mid] == target:
        return mid
    if items[mid] < target:
        return _search(items, target, mid + 1, hi)
    return _search(items, target, lo, mid - 1)


def binary_search(items, target):
    '''Return the index of target in a sorted list, or -1 when absent.'''
    return _search(items, target, 0, len(items) - 1)
