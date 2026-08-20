'''Parsing "name,score,attempts" records.'''


def parse_record(line):
    '''Return (name, score as float, attempts as int) from one record line.'''
    parts = line.split(',')
    if len(parts) != 3:
        raise ValueError('expected three comma-separated fields: ' + line)
    # Both conversions matter: everything downstream does arithmetic.
    return parts[0].strip(), float(parts[1]), int(parts[2])


def load_records(lines):
    '''Parse every non-blank line into a record tuple.'''
    records = []
    for line in lines:
        if line.strip() == '':
            continue
        records.append(parse_record(line.strip()))
    return records


def total_score(lines):
    '''Return the sum of all parsed scores.'''
    total = 0.0
    for record in load_records(lines):
        total = total + record[1]
    return total


def average_attempts(lines):
    '''Return the mean number of attempts, or 0.0 when there are no records.'''
    records = load_records(lines)
    if len(records) == 0:
        return 0.0
    total = 0
    for record in records:
        total = total + record[2]
    return total / len(records)
