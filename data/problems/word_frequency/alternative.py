'''Word counting with truthiness tests and a keyed min for the tie-break.

Sorting alphabetically and then taking the minimum by negated count picks the
same winner as the reference's explicit loop, in one expression.
'''

PUNCTUATION = '.,!?;:'


def word_counts(text, counts=None):
    '''Return a dict mapping each word of text to its number of occurrences.'''
    result = {} if counts is None else counts
    for token in text.lower().split():
        word = token.strip(PUNCTUATION)
        if word:
            result[word] = result.get(word, 0) + 1
    return result


def most_common(text):
    '''Return the most frequent word, ties broken alphabetically, else None.'''
    counts = word_counts(text)
    if not counts:
        return None
    return min(sorted(counts), key=lambda word: -counts[word])
