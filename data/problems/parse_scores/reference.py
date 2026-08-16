'''Parsing "name,score" records.'''


def parse_scores(lines):
    '''Return a dict of name -> score parsed from "name,score" lines.'''
    scores = {}
    for line in lines:
        stripped = line.strip()
        if stripped == '':
            continue
        parts = stripped.split(',')
        if len(parts) != 2:
            raise ValueError('malformed line: ' + stripped)
        # float(), not the raw string: everything downstream does arithmetic.
        scores[parts[0].strip()] = float(parts[1])
    return scores


def average_score(lines):
    '''Return the mean parsed score, or 0.0 when there are no records.'''
    scores = parse_scores(lines)
    if len(scores) == 0:
        return 0.0
    return sum(scores.values()) / len(scores)
