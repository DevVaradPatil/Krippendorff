'''Tests for text_scanner.

The repeated-call cases are the point: an accumulator hoisted to module scope
survives the first call and corrupts the second, and nothing about a single call
would reveal it. The run tests use inputs whose longest run is not the last one,
so a comparison that keeps the most recent rather than the largest fails.
'''


def normal_count_vowels(m):
    assert m.count_vowels('Hello World') == 3


def normal_longest_run(m):
    assert m.longest_run('aabbbcc') == 3


def normal_run_is_not_last(m):
    assert m.longest_run('aaabb') == 3


def edge_count_vowels_repeatable(m):
    assert m.count_vowels('education') == 5
    assert m.count_vowels('education') == 5, 'a second call disagreed with the first'


def edge_longest_run_repeatable(m):
    assert m.longest_run('aabbb') == 3
    assert m.longest_run('aabbb') == 3, 'a second call disagreed with the first'


def edge_empty_text(m):
    assert m.count_vowels('') == 0
    assert m.longest_run('') == 0


def edge_no_repeats(m):
    assert m.longest_run('abcde') == 1


def edge_all_one_character(m):
    assert m.longest_run('zzzz') == 4


TESTS = [
    {'id': 'normal_count_vowels', 'kind': 'normal', 'fn': normal_count_vowels},
    {'id': 'normal_longest_run', 'kind': 'normal', 'fn': normal_longest_run},
    {'id': 'normal_run_is_not_last', 'kind': 'normal', 'fn': normal_run_is_not_last},
    {'id': 'edge_count_vowels_repeatable', 'kind': 'edge', 'fn': edge_count_vowels_repeatable},
    {'id': 'edge_longest_run_repeatable', 'kind': 'edge', 'fn': edge_longest_run_repeatable},
    {'id': 'edge_empty_text', 'kind': 'edge', 'fn': edge_empty_text},
    {'id': 'edge_no_repeats', 'kind': 'edge', 'fn': edge_no_repeats},
    {'id': 'edge_all_one_character', 'kind': 'edge', 'fn': edge_all_one_character},
]
