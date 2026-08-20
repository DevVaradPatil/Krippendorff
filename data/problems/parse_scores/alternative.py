'''Parsing split into a per-line helper and a comprehension.

Pushing the validation into `_parse_line` lets the caller read as a single
expression, and makes the blank-line filter explicit rather than a `continue`.
'''


def _parse_line(line):
    parts = line.split(',')
    if len(parts) != 2:
        raise ValueError('malformed line: ' + line)
    return parts[0].strip(), float(parts[1])


def parse_scores(lines):
    '''Return a dict of name -> score parsed from "name,score" lines.'''
    return dict(_parse_line(line.strip()) for line in lines if line.strip() != '')


def average_score(lines):
    '''Return the mean parsed score, or 0.0 when there are no records.'''
    scores = parse_scores(lines)
    return sum(scores.values()) / len(scores) if scores else 0.0
