from collections import OrderedDict
from itertools import product
import re
from sre_constants import CATEGORY_DIGIT, CATEGORY_NOT_DIGIT, CATEGORY_SPACE, CATEGORY_NOT_SPACE, CATEGORY, NEGATE, \
    RANGE, LITERAL, IN, MAX_REPEAT, AT, SUBPATTERN, GROUPREF, BRANCH
from sre_parse import DIGITS, WHITESPACE
import string
import unittest

ALLOWED_URL_CHARACTERS = set(string.digits + string.ascii_letters + string.punctuation)

CATEGORY_MAP = {
    CATEGORY_DIGIT: DIGITS,
    CATEGORY_NOT_DIGIT: ALLOWED_URL_CHARACTERS - DIGITS,
    CATEGORY_SPACE: WHITESPACE,
    CATEGORY_NOT_SPACE: ALLOWED_URL_CHARACTERS - WHITESPACE,
}


def parse_at(clause, context):
    yield '', [], []


def parse_branch(clause, context):
    _, subpatterns = clause
    for subpattern in subpatterns:
        yield from _normalize(subpattern, context)


def parse_groupref(clause, context):
    group_id = clause
    group_name = context['pattern_reverse_groupdict'].get(group_id, '_%d' % group_id)
    yield '%%(%s)s' % group_name, [], [group_name]


def parse_in(clause, context):
    assert len(clause)
    in_clause_type, in_clause_value = clause[0]
    if in_clause_type == NEGATE:
        # e.g. ('negate', None)
        candidate_ascii = set(ALLOWED_URL_CHARACTERS)
        for in_clause_type, in_clause_value in clause[1:]:
            if in_clause_type == RANGE:
                candidate_ascii -= map(chr, range(in_clause_value[0], in_clause_value[1] + 1))
            elif in_clause_type == CATEGORY:
                try:
                    candidate_ascii -= CATEGORY_MAP[in_clause_value]
                except KeyError:
                    raise NotImplementedError(
                        '%s category is not supported in character classes.' % in_clause_value)
            else:
                assert in_clause_type == 'literal'
                candidate_ascii.discard(chr(in_clause_value))
        yield min(candidate_ascii), [], []
    elif in_clause_type == LITERAL:
        # e.g. ('literal', 97)
        yield chr(in_clause_value), [], []
    elif in_clause_type == CATEGORY:
        try:
            yield min(CATEGORY_MAP[in_clause_value]), [], []
        except KeyError:
            raise NotImplementedError('%s category is not supported in character classes.' % in_clause_value)
    elif in_clause_type == RANGE:
        # e.g. ('range', (99, 100))
        yield chr(in_clause_value[0]), [], []


def parse_literal(clause, context):
    yield (chr(clause), [], [])


def parse_max_repeat(clause, context):
    min_repeat, max_repeat, subpattern = clause
    if min_repeat == 0:
        yield '', [], []
        assert max_repeat > 0
        min_repeat = 1
    for format_string, args, refs in _normalize(subpattern, context):
        yield format_string * min_repeat, args, refs


def parse_subpattern(clause, context):
    group_id, subpattern = clause

    if group_id is not None:
        # Entering for capturing-groups only
        if group_id in context['pattern_reverse_groupdict']:
            # named groups only
            group_name = context['pattern_reverse_groupdict'][group_id]
            if group_name[0] == '_' and group_name[1:].isdigit():
                raise ValueError('Group name cannot have format `_\\d+`')
            yield '%%(%s)s' % group_name, [group_name], []
        elif not context['in_unnamed_group']:
            # unnamed groups not inside another unnamed group
            # format strings cannot have unnamed groups nested because there is no way to provide
            # positional argument not starting from fist one

            group_name = '_%d' % group_id
            context = dict(context)
            context['in_unnamed_group'] = True
            yield '%%(%s)s' % group_name, [group_name], []

    for format_strings, args, refs in _normalize(subpattern, context):
        if args:
            yield format_strings, args, refs
            # for format_strings, args in _normalize(subpattern, context):
            #     if group_id in context['pattern_reverse_groupdict']:
            #         yield format_strings, args
            #     else:


dispatch_table = {
    AT: parse_at,
    BRANCH: parse_branch,
    GROUPREF: parse_groupref,
    IN: parse_in,
    LITERAL: parse_literal,
    MAX_REPEAT: parse_max_repeat,
    SUBPATTERN: parse_subpattern,
}


def reverse_groupdict(pattern_groupdict):
    return {v: k for k, v in pattern_groupdict.items()}


def unique_list(l):
    return list(OrderedDict.fromkeys(l).keys())


def normalize(pattern):
    pattern_parse_tree = re.sre_parse.parse(pattern)
    pattern_groupdict = pattern_parse_tree.pattern.groupdict
    pattern_reverse_groupdict = reverse_groupdict(pattern_groupdict)
    for format_string, args, refs in _normalize(pattern_parse_tree,
                                                {'pattern_reverse_groupdict': pattern_reverse_groupdict,
                                                 'in_unnamed_group': False}):
        unresolved_refs = set(refs)
        for arg in args:
            unresolved_refs.discard(arg)
        if not unresolved_refs:
            yield format_string, args


def _normalize(pattern_parse_tree, context):
    parse_tree = [handle_clause(c, context) for c in pattern_parse_tree]
    for format_strings in product(*parse_tree):
        args = sum((f[1] for f in format_strings), [])
        args = unique_list(args)
        refs = sum((f[2] for f in format_strings), [])
        refs = list(set(refs))
        yield ''.join(f[0] for f in format_strings), args, refs


def handle_clause(clause, context):
    clause_type, clause_value = clause
    yield from dispatch_table[clause_type](clause_value, context)


class RegexParserTestCase(unittest.TestCase):
    def test_reverse_groupdict(self):
        self.assertEqual(reverse_groupdict({'a': 1, 'b': 2}), {1: 'a', 2: 'b'})

    def test_normalize_named_groups_1(self):
        self.assertEqual(list(normalize('test(?P<P>groupP)')),
                         [
                             ('test%(P)s', ['P']),
                         ])

    def test_normalize_named_groups_2(self):
        self.assertEqual(list(normalize('test(?P<P>groupP)?')),
                         [
                             ('test', []),
                             ('test%(P)s', ['P']),
                         ])

    def test_normalize_named_groups_3(self):
        self.assertEqual(list(normalize('test(?P<A>groupA(?P<A1>groupA1)(?P<A2>groupA2))?')),
                         [('test', []),
                          ('test%(A)s', ['A']),
                          ('testgroupA%(A1)s%(A2)s', ['A1', 'A2']),
                         ]
        )

    def test_normalize_unnamed_groups_1(self):
        self.assertEqual(list(normalize('test(groupP)')),
                         [
                             ('test%(_1)s', ['_1']),
                         ])

    def test_normalize_unnamed_groups_2(self):
        self.assertEqual(list(normalize('test(groupP)?')),
                         [
                             ('test', []),
                             ('test%(_1)s', ['_1']),
                         ])


    def test_normalize_unnamed_groups_3(self):
        self.assertEqual(list(normalize('test(groupA(groupA1)(groupA2))?')),
                         [
                             ('test', []),
                             ('test%(_1)s', ['_1']),
                         ]
        )


    def test_normalize_unnamed_groups_3a(self):
        self.assertEqual(list(normalize('test(groupA(groupA1)(groupA2))(groupB(groupB1)(groupB2))')),
                         [
                             ('test%(_1)s%(_4)s', ['_1', '_4']),
                         ]
        )

    def test_normalize_class_1(self):
        self.assertEqual(list(normalize('[test](group)')),
                         [
                             ('t%(_1)s', ['_1']),
                         ]
        )


    def test_normalize_class_2(self):
        self.assertEqual(list(normalize('[^test](group)')),
                         [
                             ('!%(_1)s', ['_1']),
                         ]
        )


    def test_normalize_at(self):
        self.assertEqual(list(normalize('^[^test](group)$')),
                         [
                             ('!%(_1)s', ['_1']),
                         ]
        )


    def test_normalize_category_1(self):
        self.assertEqual(list(normalize('\d')),
                         [
                             ('0', []),
                         ]
        )


    def test_normalize_category_2(self):
        self.assertEqual(list(normalize('[\d]')),
                         [
                             ('0', []),
                         ]
        )


    def test_normalize_category_3(self):
        self.assertEqual(list(normalize('[^\d]')),
                         [
                             ('!', []),
                         ]
        )

    def test_normalize_category_3a(self):
        self.assertEqual(list(normalize('[^\D]')),
                         [
                             ('0', []),
                         ]
        )

    def test_normalize_category_3b(self):
        self.assertEqual(list(normalize('\D')),
                         [
                             ('!', []),
                         ]
        )


    def test_normalize_category_4(self):
        def bad_call():
            list(normalize('[^\w]'))

        self.assertRaises(NotImplementedError, bad_call)


    def test_normalize_category_5(self):
        self.assertEqual(list(normalize('\s')),
                         [
                             ('\t', []),
                         ]
        )


    def test_normalize_category_6(self):
        self.assertEqual(list(normalize('[\s]')),
                         [
                             ('\t', []),
                         ]
        )


    def test_normalize_category_7(self):
        self.assertEqual(list(normalize('[^\s]')),
                         [
                             ('!', []),
                         ]
        )

    def test_normalize_backrefs_1(self):
        self.assertEqual(list(normalize('([a-z])/\\1')),
                         [
                             ('%(_1)s/%(_1)s', ['_1']),
                         ]
        )

    def test_normalize_backrefs_named(self):
        self.assertEqual(list(normalize('(?P<a>[a-z]+)/(?P=a)')),
                         [
                             ('%(a)s/%(a)s', ['a']),
                         ]
        )

    def test_normalize_backrefs_nested(self):
        self.assertEqual(list(normalize('(?P<a>(?P<a1>[a-z]+)(?P<a2>\d+))/(?P=a)')),
                         [
                             ('%(a)s/%(a)s', ['a']),
                         ]
        )

    def test_normalize_backrefs_nested2(self):
        self.assertEqual(list(normalize('(?P<a>(?P<a1>[a-z]+)(?P<a2>\d+))/(?P=a2)')),
                         [
                             ('%(a1)s%(a2)s/%(a2)s', ['a1', 'a2']),
                         ]
        )


    def test_normalize_bad_group_name(self):
        def bad_name():
            list(normalize('(?P<_1>group)'))

        self.assertRaises(ValueError, bad_name)


    def test_unique_list(self):
        self.assertEqual(unique_list([9, 1, 2, 1, 1, 3]), [9, 1, 2, 3])


    def test_alternation_1(self):
        self.assertEqual(list(normalize('(first)|(second)')),
                         [
                             ('%(_1)s', ['_1']),
                             ('%(_2)s', ['_2']),
                         ]
        )

    def test_alternation_2(self):
        self.assertEqual(list(normalize('(?P<A>(?P<B>b)|(?P<C>c))')),
                         [
                             ('%(A)s', ['A']),
                             ('%(B)s', ['B']),
                             ('%(C)s', ['C']),
                         ]
        )


if __name__ == '__main__':
    unittest.main()