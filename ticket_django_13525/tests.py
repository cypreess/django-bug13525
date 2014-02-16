from itertools import product


def group_normalize(pattern):
    results = _group_normalize(None, pattern)
    return list(results)

def _group_normalize(name, pattern):

    if name is not None:
        yield name
    groups = map(parse_group, _groups(pattern))

    nested = [_group_normalize(g[0], g[1]) for g in groups]
    if nested:
        yield from product(*nested)



def _groups(pattern):
    depth = 0
    start = None
    for i, c in enumerate(pattern):
        if c == '(':
            if depth == 0:
                start = i
            depth += 1
        elif c == ')':
            depth -= 1

        if depth == 0:
            yield pattern[start:i + 1]
            start = None
    assert depth == 0


def parse_group(pattern):
    assert pattern[0] == '('
    assert pattern[-1] == ')'
    name = ''
    for i, c in enumerate(pattern[1:]):
        if c not in '()':
            name += c
        else:
            return name, pattern[i + 1:-1]


inp = '(A(A1)(A2))(B(B1))(C)(A)'
output = ['A B C', 'A1 A2 B C', 'A B1 C', 'A1 A2 B1 C']

from pprint import pprint
pprint(group_normalize(inp))