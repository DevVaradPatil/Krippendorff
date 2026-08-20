'''Scanning text for vowels and repeated runs.'''

VOWELS = 'aeiou'


def count_vowels(text):
    '''Return the number of vowels in the text, ignoring case.'''
    total = 0
    for character in text.lower():
        if character not in VOWELS:
            continue
        total = total + 1
    return total


def longest_run(text):
    '''Return the length of the longest run of one repeated character.'''
    best = 0
    current = 0
    previous = ''
    for character in text:
        if character == previous:
            current = current + 1
        else:
            current = 1
        previous = character
        if current > best:
            best = current
    return best
