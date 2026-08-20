'''Conversion driven by a lookup of per-unit functions.'''

CONVERTERS = {
    'C': lambda value: value,
    'F': lambda value: (value - 32.0) * 5.0 / 9.0,
}


def parse_reading(text):
    '''Return (value, unit) from a "value unit" reading.'''
    parts = text.split()
    if len(parts) != 2:
        raise ValueError('expected a value and a unit: ' + text)
    return float(parts[0]), parts[1].upper()


def to_celsius(readings):
    '''Convert readings to Celsius, skipping blank entries.'''
    out = []
    for text in readings:
        if text.strip():
            value, unit = parse_reading(text.strip())
            out.append(CONVERTERS.get(unit, CONVERTERS['F'])(value))
    return out
