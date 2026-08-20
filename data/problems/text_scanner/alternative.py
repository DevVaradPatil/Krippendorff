'''The same scans using sum() and itertools.groupby.'''

import itertools

VOWELS = 'aeiou'


def count_vowels(text):
    '''Return the number of vowels in the text, ignoring case.'''
    return sum(1 for character in text.lower() if character in VOWELS)


def longest_run(text):
    '''Return the length of the longest run of one repeated character.'''
    runs = [len(list(group)) for _, group in itertools.groupby(text)]
    return max(runs) if runs else 0
