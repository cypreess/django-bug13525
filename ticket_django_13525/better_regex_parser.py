from collections import OrderedDict, namedtuple
from itertools import product
import re
from sre_constants import CATEGORY_DIGIT, CATEGORY_NOT_DIGIT, CATEGORY_SPACE, CATEGORY_NOT_SPACE, CATEGORY, NEGATE, \
    RANGE, LITERAL, IN, MAX_REPEAT, AT, SUBPATTERN, GROUPREF, BRANCH, ANY, NOT_LITERAL, CATEGORY_WORD, CATEGORY_NOT_WORD
from sre_parse import DIGITS, WHITESPACE
import string

ALLOWED_URL_CHARACTERS = set(string.digits + string.ascii_letters + string.punctuation)

Category = namedtuple('Category', ('char_set', 'default_mapping'))

Context = namedtuple('Context', ('pattern_reverse_groupdict', 'in_unnamed_group'))

CATEGORY_MAP = {
    CATEGORY_DIGIT: Category(DIGITS, '0'),
    CATEGORY_NOT_DIGIT: Category(ALLOWED_URL_CHARACTERS - DIGITS, 'x'),
    CATEGORY_SPACE: Category(WHITESPACE, ' '),
    CATEGORY_NOT_SPACE: Category(ALLOWED_URL_CHARACTERS - WHITESPACE, 'x'),
    CATEGORY_WORD: Category(set(string.ascii_letters + string.digits + '_'), 'X'),
    CATEGORY_NOT_WORD: Category(set(string.ascii_letters + string.digits + '_'), '!'),
}


def parse_at(clause, context):
    """
    >>> re.sre_parse.parse('^$')
    [('at', 'at_beginning'), ('at', 'at_end')]
    """
    yield '', [], []


def parse_any(clause, context):
    """
    >>> re.sre_parse.parse('.')
    [('any', None)]
    """
    yield '.', [], []


def parse_branch(clause, context):
    _, subpatterns = clause
    for subpattern in subpatterns:
        yield from _normalize(subpattern, context)


def parse_groupref(clause, context):
    group_id = clause
    group_name = context.pattern_reverse_groupdict.get(group_id, '_%d' % (group_id - 1))
    yield '%%(%s)s' % group_name, [], [group_name]


def parse_in(clause, context):
    """
    >>> re.sre_parse.parse('[a-z]')
    [('in', [('range', (97, 122))])]
    """
    assert len(clause)
    in_clause_type, in_clause_value = clause[0]
    if in_clause_type == NEGATE:
        # e.g. ('negate', None)
        candidate_ascii = set(ALLOWED_URL_CHARACTERS)
        for in_clause_type, in_clause_value in clause[1:]:
            if in_clause_type == RANGE:
                candidate_ascii -= set(map(chr, range(in_clause_value[0], in_clause_value[1] + 1)))
            elif in_clause_type == CATEGORY:
                try:
                    candidate_ascii -= CATEGORY_MAP[in_clause_value].char_set
                except KeyError:
                    raise NotImplementedError(
                        '%s category is not supported in character classes.' % in_clause_value)
            else:
                assert in_clause_type == 'literal'
                candidate_ascii.discard(chr(in_clause_value))
        yield min(candidate_ascii), [], []
    elif in_clause_type == LITERAL:
        # e.g. ('literal', 97)
        yield from parse_literal(in_clause_value, context)
    elif in_clause_type == CATEGORY:
        try:
            yield CATEGORY_MAP[in_clause_value].default_mapping, [], []
        except KeyError:
            raise NotImplementedError('%s category is not supported in character classes.' % in_clause_value)
    elif in_clause_type == RANGE:
        # e.g. ('range', (99, 100))
        yield chr(in_clause_value[0]), [], []


def parse_literal(clause, context):
    """
    >>> re.sre_parse.parse('a')
    [('literal', 97)]
    """
    yield (chr(clause), [], [])


def parse_not_literal(clause, context):
    """
    >>> re.sre_parse.parse('[^a]')
    [('not_literal', 97)]
    """
    candidate_ascii = set(ALLOWED_URL_CHARACTERS)
    candidate_ascii.discard(chr(clause))
    yield min(candidate_ascii), [], []


def parse_max_repeat(clause, context):
    """
    >>> re.sre_parse.parse('a{3,5}')
    [('max_repeat', (3, 5, [('literal', 97)]))]
    """
    min_repeat, max_repeat, subpattern = clause
    repeat = min_repeat
    if repeat == 0:
        yield '', [], []
        assert max_repeat > 0
        repeat = 1
    for format_string, args, refs in _normalize(subpattern, context):
        if not min_repeat == 0 or args or refs:
            yield format_string * repeat, args, refs


def parse_subpattern(clause, context):
    """
    >>> re.sre_parse.parse('(a)')
    [('subpattern', (1, [('literal', 97)]))]
    """
    group_id, subpattern = clause

    if group_id is not None:
        # Entering for capturing-groups only
        if group_id in context.pattern_reverse_groupdict:
            # named groups only
            group_name = context.pattern_reverse_groupdict[group_id]
            if group_name[0] == '_' and group_name[1:].isdigit():
                raise ValueError('Group name cannot have format `_\\d+`')
            yield '%%(%s)s' % group_name, [group_name], []
        elif not context.in_unnamed_group:
            # unnamed groups not inside another unnamed group
            # format strings cannot have unnamed groups nested because there is no way to provide
            # positional argument not starting from fist one

            group_name = '_%d' % (group_id - 1)  # unnamed groups are counted from 0 rather then 1
            context = context._replace(in_unnamed_group=True)
            yield '%%(%s)s' % group_name, [group_name], []

    for format_strings, args, refs in _normalize(subpattern, context):
        if args or group_id is None:
            yield format_strings, args, refs


DISPATCH_TABLE = {
    ANY: parse_any,
    AT: parse_at,
    BRANCH: parse_branch,
    GROUPREF: parse_groupref,
    IN: parse_in,
    LITERAL: parse_literal,
    MAX_REPEAT: parse_max_repeat,
    NOT_LITERAL: parse_not_literal,
    SUBPATTERN: parse_subpattern,
}


def reverse_groupdict(pattern_groupdict):
    """
    Switches dict keys with values and return new dict
    """
    return {v: k for k, v in pattern_groupdict.items()}


def unique_list(l):
    """
    Stable list unique.
    """
    return list(OrderedDict.fromkeys(l).keys())


def normalize_list(pattern):
    return list(normalize(pattern))


def normalize(pattern):
    pattern_parse_tree = re.sre_parse.parse(pattern)
    pattern_groupdict = pattern_parse_tree.pattern.groupdict
    pattern_reverse_groupdict = reverse_groupdict(pattern_groupdict)
    for format_string, args, refs in _normalize(pattern_parse_tree,
                                                Context(pattern_reverse_groupdict, False)):
        unresolved_refs = set(refs)
        for arg in args:
            unresolved_refs.discard(arg)
        if not unresolved_refs:
            yield format_string, args


def _normalize(pattern_parse_tree, context):
    parse_tree = [dispatch_clause(c, context) for c in pattern_parse_tree]
    for format_strings in product(*parse_tree):
        args = sum((f[1] for f in format_strings), [])
        args = unique_list(args)
        refs = sum((f[2] for f in format_strings), [])
        refs = list(set(refs))
        yield ''.join(f[0] for f in format_strings), args, refs


def dispatch_clause(clause, context):
    """
    Dispatches a single clause depending its type and yields format strings propositions
    """
    clause_type, clause_value = clause
    yield from DISPATCH_TABLE[clause_type](clause_value, context)

