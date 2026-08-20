'''Tests for student_records.

Each converted field is exercised by arithmetic rather than by equality alone:
a dropped float() or int() then fails here, instead of silently producing a
tuple of strings that breaks somewhere unrelated later.
'''


ROWS = ['ana,90.5,3', 'bo,85.0,1', 'cy,70.5,5']


def normal_parse_one(m):
    assert m.parse_record('ana,90.5,3') == ('ana', 90.5, 3)


def normal_scores_are_numbers(m):
    assert abs(m.total_score(ROWS) - 246.0) < 1e-9


def normal_attempts_are_numbers(m):
    assert abs(m.average_attempts(ROWS) - 3.0) < 1e-9


def normal_load_all(m):
    assert len(m.load_records(ROWS)) == 3


def edge_blank_line_in_the_middle(m):
    assert len(m.load_records(['ana,90.5,3', '', 'bo,85.0,1'])) == 2


def edge_no_records(m):
    assert m.load_records([]) == []
    assert abs(m.average_attempts([]) - 0.0) < 1e-12


def edge_fractional_average(m):
    # 3 and 2 attempts average to 2.5, so integer division changes the answer.
    assert abs(m.average_attempts(['ana,1.0,3', 'bo,1.0,2']) - 2.5) < 1e-12


def degenerate_wrong_field_count(m):
    try:
        m.parse_record('ana,90.5')
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for a two-field line')


TESTS = [
    {'id': 'normal_parse_one', 'kind': 'normal', 'fn': normal_parse_one},
    {'id': 'normal_scores_are_numbers', 'kind': 'normal', 'fn': normal_scores_are_numbers},
    {'id': 'normal_attempts_are_numbers', 'kind': 'normal', 'fn': normal_attempts_are_numbers},
    {'id': 'normal_load_all', 'kind': 'normal', 'fn': normal_load_all},
    {'id': 'edge_blank_line_in_the_middle', 'kind': 'edge', 'fn': edge_blank_line_in_the_middle},
    {'id': 'edge_no_records', 'kind': 'edge', 'fn': edge_no_records},
    {'id': 'edge_fractional_average', 'kind': 'edge', 'fn': edge_fractional_average},
    {'id': 'degenerate_wrong_field_count', 'kind': 'degenerate', 'fn': degenerate_wrong_field_count},
]
