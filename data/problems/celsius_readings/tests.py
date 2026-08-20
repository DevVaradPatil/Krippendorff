'''Tests for celsius_readings.

normal_fahrenheit picks a value whose conversion is not a whole number, so floor
division changes the answer. At 212 F the result is exactly 100 either way and
the bug would hide.
'''


def normal_celsius_passthrough(m):
    assert abs(m.to_celsius(['20 C'])[0] - 20.0) < 1e-9


def normal_fahrenheit(m):
    assert abs(m.to_celsius(['72.5 F'])[0] - 22.5) < 1e-9


def normal_mixed(m):
    result = m.to_celsius(['32 F', '100 C'])
    assert abs(result[0] - 0.0) < 1e-9
    assert abs(result[1] - 100.0) < 1e-9


def normal_parse_reading(m):
    assert m.parse_reading('12.5 c') == (12.5, 'C')


def edge_blank_entries_skipped(m):
    assert len(m.to_celsius(['20 C', '   ', '30 C'])) == 2


def edge_negative_fahrenheit(m):
    assert abs(m.to_celsius(['-40 F'])[0] + 40.0) < 1e-9


def degenerate_malformed_reading(m):
    try:
        m.parse_reading('20C')
    except ValueError:
        return
    except Exception as exc:
        raise AssertionError('expected ValueError, got ' + type(exc).__name__)
    raise AssertionError('expected ValueError for a reading with no separator')


TESTS = [
    {'id': 'normal_celsius_passthrough', 'kind': 'normal', 'fn': normal_celsius_passthrough},
    {'id': 'normal_fahrenheit', 'kind': 'normal', 'fn': normal_fahrenheit},
    {'id': 'normal_mixed', 'kind': 'normal', 'fn': normal_mixed},
    {'id': 'normal_parse_reading', 'kind': 'normal', 'fn': normal_parse_reading},
    {'id': 'edge_blank_entries_skipped', 'kind': 'edge', 'fn': edge_blank_entries_skipped},
    {'id': 'edge_negative_fahrenheit', 'kind': 'edge', 'fn': edge_negative_fahrenheit},
    {'id': 'degenerate_malformed_reading', 'kind': 'degenerate', 'fn': degenerate_malformed_reading},
]
