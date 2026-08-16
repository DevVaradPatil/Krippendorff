'''Tests for parse_scores.

`normal_values_are_numbers` compares against floats rather than checking a
string equality, so leaving out the `float()` conversion fails here rather than
silently producing a dict of strings that only breaks in arithmetic later.

`edge_blank_line_is_skipped` puts the blank line in the middle: a `return` where
`continue` was meant truncates the results, which a trailing blank line would
not reveal.
'''


def normal_two_records(m):
    assert m.parse_scores(['ana,90', 'bo,80']) == {'ana': 90.0, 'bo': 80.0}


def normal_values_are_numbers(m):
    parsed = m.parse_scores(['ana,90.5'])
    assert parsed['ana'] == 90.5
    assert abs(parsed['ana'] * 2 - 181.0) < 1e-12


def normal_average(m):
    assert abs(m.average_score(['ana,90', 'bo,81']) - 85.5) < 1e-12


def edge_blank_line_is_skipped(m):
    parsed = m.parse_scores(['ana,90', '', 'bo,80'])
    assert parsed == {'ana': 90.0, 'bo': 80.0}, 'got ' + repr(parsed)


def edge_whitespace(m):
    assert m.parse_scores(['  ana , 90 ']) == {'ana': 90.0}


def edge_no_records(m):
    assert m.parse_scores([]) == {}
    assert abs(m.average_score([]) - 0.0) < 1e-12


def degenerate_malformed_line(m):
    try:
        m.parse_scores(['ana'])
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for a line without a comma')


TESTS = [
    {'id': 'normal_two_records', 'kind': 'normal', 'fn': normal_two_records},
    {'id': 'normal_values_are_numbers', 'kind': 'normal', 'fn': normal_values_are_numbers},
    {'id': 'normal_average', 'kind': 'normal', 'fn': normal_average},
    {'id': 'edge_blank_line_is_skipped', 'kind': 'edge', 'fn': edge_blank_line_is_skipped},
    {'id': 'edge_whitespace', 'kind': 'edge', 'fn': edge_whitespace},
    {'id': 'edge_no_records', 'kind': 'edge', 'fn': edge_no_records},
    {'id': 'degenerate_malformed_line', 'kind': 'degenerate', 'fn': degenerate_malformed_line},
]
