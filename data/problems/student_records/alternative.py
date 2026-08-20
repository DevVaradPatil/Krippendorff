'''The same parsing built from comprehensions and built-ins.'''


def parse_record(line):
    '''Return (name, score as float, attempts as int) from one record line.'''
    parts = line.split(',')
    if len(parts) != 3:
        raise ValueError('expected three comma-separated fields: ' + line)
    return parts[0].strip(), float(parts[1]), int(parts[2])


def load_records(lines):
    '''Parse every non-blank line into a record tuple.'''
    return [parse_record(line.strip()) for line in lines if line.strip() != '']


def total_score(lines):
    '''Return the sum of all parsed scores.'''
    return sum(record[1] for record in load_records(lines))


def average_attempts(lines):
    '''Return the mean number of attempts, or 0.0 when there are no records.'''
    records = load_records(lines)
    if not records:
        return 0.0
    return sum(record[2] for record in records) / len(records)
