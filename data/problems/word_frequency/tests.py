'''Tests for word_frequency.

`normal_tie_broken_alphabetically` pins the comparison operator: with `>=` the
last word of a tie wins instead of the first. `edge_single_occurrence_wins`
pins the accumulator's starting value: initialised to 1 rather than 0, a word
seen once can never become the maximum. `edge_repeated_calls` catches both a
mutable default argument and an accumulator lifted to module scope.
'''


def normal_counts(m):
    assert m.word_counts('the cat the hat') == {'the': 2, 'cat': 1, 'hat': 1}


def normal_case_and_punctuation(m):
    assert m.word_counts('Hello, hello! World.') == {'hello': 2, 'world': 1}


def normal_tie_broken_alphabetically(m):
    assert m.most_common('pear apple pear apple') == 'apple'


def normal_clear_winner(m):
    assert m.most_common('a b b c b') == 'b'


def edge_single_occurrence_wins(m):
    assert m.most_common('solo') == 'solo'


def edge_no_words(m):
    assert m.most_common('') is None
    assert m.most_common('...') is None


def edge_repeated_calls(m):
    first = m.word_counts('one two')
    second = m.word_counts('one two')
    assert first == {'one': 1, 'two': 1}
    assert second == {'one': 1, 'two': 1}, 'a second call returned ' + repr(second)


TESTS = [
    {'id': 'normal_counts', 'kind': 'normal', 'fn': normal_counts},
    {'id': 'normal_case_and_punctuation', 'kind': 'normal', 'fn': normal_case_and_punctuation},
    {'id': 'normal_tie_broken_alphabetically', 'kind': 'normal', 'fn': normal_tie_broken_alphabetically},
    {'id': 'normal_clear_winner', 'kind': 'normal', 'fn': normal_clear_winner},
    {'id': 'edge_single_occurrence_wins', 'kind': 'edge', 'fn': edge_single_occurrence_wins},
    {'id': 'edge_no_words', 'kind': 'edge', 'fn': edge_no_words},
    {'id': 'edge_repeated_calls', 'kind': 'edge', 'fn': edge_repeated_calls},
]
