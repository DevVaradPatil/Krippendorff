'''Binary search over a sorted list.'''


def binary_search(items, target):
    '''Return the index of target in a sorted list, or -1 when absent.'''
    lo = 0
    # The last valid index, not the length: hi is inclusive below.
    hi = len(items) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if items[mid] == target:
            return mid
        if items[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1
