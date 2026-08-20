'''Normalising temperature readings to Celsius.'''


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
        if text.strip() == '':
            continue
        value, unit = parse_reading(text.strip())
        if unit == 'C':
            out.append(value)
        else:
            # The 5/9 must stay a true division or every result collapses.
            out.append((value - 32.0) * 5.0 / 9.0)
    return out
