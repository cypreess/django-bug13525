from collections import OrderedDict
from itertools import product
import re
import unittest



def parse_at(clause, context):
    return

def parse_in(clause, context):
    assert len(clause)
    in_clause_type, in_clause_value = clause[0]
    if in_clause_type == 'negate':
        # e.g. ('negate', None)
        yield '', []
    elif in_clause_type == 'literal':
        # e.g. ('literal', 97)
        yield chr(in_clause_value), []
    elif in_clause_type == 'range':
        # e.g. ('range', (99, 100))
        yield chr(in_clause_value[0])


def parse_literal(clause, context):
    yield (chr(clause), [])


def parse_max_repeat(clause, context):
    min_repeat, max_repeat, subpattern = clause
    if min_repeat == 0:
        yield '', []
        assert max_repeat > 0
        min_repeat = 1
    for format_string, args in _normalize(subpattern, context):
        yield format_string * min_repeat, args


def parse_subpattern(clause, context):
    group_id, subpattern = clause

    if group_id is not None:
        # Entering for capturing-groups only
        if group_id in context['pattern_reverse_groupdict']:
            # named groups only
            group_name = context['pattern_reverse_groupdict'][group_id]
            if group_name[0] == '_' and group_name[1:].isdigit():
                raise ValueError('Group name cannot have format `_\\d+`')
            yield '%%(%s)s' % group_name, [group_name]
        elif not context['in_unnamed_group']:
            # unnamed groups not inside another unnamed group
            # format strings cannot have unnamed groups nested because there is no way to provide
            # positional argument not starting from fist one

            group_name = '_%d' % group_id
            context = dict(context)
            context['in_unnamed_group'] = True
            yield '%%(%s)s' % group_name, [group_name]

    for format_strings, args in _normalize(subpattern, context):
        if args:
            yield format_strings, args
            # for format_strings, args in _normalize(subpattern, context):
            #     if group_id in context['pattern_reverse_groupdict']:
            #         yield format_strings, args
            #     else:


dispatch_table = {
    'in': parse_in,
    'max_repeat': parse_max_repeat,
    'at': parse_at,
    'literal': parse_literal,
    'subpattern': parse_subpattern,
}


def reverse_groupdict(pattern_groupdict):
    return {v: k for k, v in pattern_groupdict.items()}


def unique_list(l):
    return list(OrderedDict.fromkeys(l).keys())


def normalize(pattern):
    pattern_parse_tree = re.sre_parse.parse(pattern)
    pattern_groupdict = pattern_parse_tree.pattern.groupdict
    pattern_reverse_groupdict = reverse_groupdict(pattern_groupdict)
    yield from _normalize(pattern_parse_tree,
                          {'pattern_reverse_groupdict': pattern_reverse_groupdict, 'in_unnamed_group': False})
    # for format_string in _normalize(pattern_parse_tree, pattern_reverse_groupdict):
    #     yield format_string
    #     print(list(f for f in format_string))
    # yield ''.join(f[0] for f in format_string), list(OrderedDict.fromkeys(sum((f[1] for f in format_string), [])))


def _normalize(pattern_parse_tree, context):
    parse_tree = [handle_clause(c, context) for c in pattern_parse_tree]
    for format_strings in product(*parse_tree):
        s = sum((f[1] for f in format_strings), [])
        yield ''.join(f[0] for f in format_strings), unique_list(s)


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



    def test_normalize_bad_group_name(self):
        def bad_name():
            list(normalize('(?P<_1>group)'))
        self.assertRaises(ValueError, bad_name)



    def test_unique_list(self):
        self.assertEqual(unique_list([9, 1, 2, 1, 1, 3]), [9, 1, 2, 3])


if __name__ == '__main__':
    unittest.main()