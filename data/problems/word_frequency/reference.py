'''Word frequency counting.'''

PUNCTUATION = '.,!?;:'


def word_counts(text, counts=None):
    '''Return a dict mapping each word of text to its number of occurrences.'''
    if counts is None:
        counts = {}
    for token in text.lower().split():
        word = token.strip(PUNCTUATION)
        if word == '':
            continue
        counts[word] = counts.get(word, 0) + 1
    return counts


def most_common(text):
    '''Return the most frequent word, ties broken alphabetically, else None.'''
    counts = word_counts(text)
    best = None
    best_count = 0
    # sorted() first, and a strict >, so the alphabetically earliest of a tie
    # is the one that wins.
    for word in sorted(counts):
        if counts[word] > best_count:
            best = word
            best_count = counts[word]
    return best
