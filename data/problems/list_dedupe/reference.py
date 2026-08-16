'''Order-preserving list deduplication.'''


def dedupe(items, seen=None):
    '''Return a new list with duplicates removed, order of first use preserved.'''
    # `None` rather than an empty set as the default: a mutable default is
    # created once at definition time and would leak between calls.
    if seen is None:
        seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def merged_unique(a, b):
    '''Return the unique items of a, then any items of b not already present.'''
    # Copy: assigning `a` directly would make the caller's list grow below.
    result = list(dedupe(a))
    for item in dedupe(b):
        if item not in result:
            result.append(item)
    return result
