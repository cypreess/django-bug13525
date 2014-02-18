import unittest

from better_regex_parser import normalize, reverse_groupdict, unique_list


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
                         [
                             ('test', []),
                             ('test%(A)s', ['A']),
                             ('testgroupA%(A1)s%(A2)s', ['A1', 'A2']),
                         ])

    def test_normalize_unnamed_groups_1(self):
        self.assertEqual(list(normalize('test(groupP)')),
                         [
                             ('test%(_0)s', ['_0']),
                         ])

    def test_normalize_unnamed_groups_2(self):
        self.assertEqual(list(normalize('test(groupP)?')),
                         [
                             ('test', []),
                             ('test%(_0)s', ['_0']),
                         ])

    def test_normalize_unnamed_groups_3(self):
        self.assertEqual(list(normalize('test(groupA(groupA1)(groupA2))?')),
                         [
                             ('test', []),
                             ('test%(_0)s', ['_0']),
                         ])

    def test_normalize_unnamed_groups_3a(self):
        self.assertEqual(list(normalize('test(groupA(groupA1)(groupA2))(groupB(groupB1)(groupB2))')),
                         [
                             ('test%(_0)s%(_3)s', ['_0', '_3']),
                         ])

    def test_normalize_class_1(self):
        self.assertEqual(list(normalize('[test](group)')),
                         [
                             ('t%(_0)s', ['_0']),
                         ])

    def test_normalize_class_2(self):
        self.assertEqual(list(normalize('[^test](group)')),
                         [
                             ('!%(_0)s', ['_0']),
                         ])

    def test_normalize_class_3(self):
        self.assertEqual(list(normalize('[^!-#](group)')),
                         [
                             ('$%(_0)s', ['_0']),
                         ])

    def test_normalize_class_4(self):
        self.assertEqual(list(normalize('[^!](group)')),
                         [
                             ('"%(_0)s', ['_0']),
                         ])

    def test_normalize_at(self):
        self.assertEqual(list(normalize('^[^test](group)$')),
                         [
                             ('!%(_0)s', ['_0']),
                         ])

    def test_normalize_category_1(self):
        self.assertEqual(list(normalize('\d')),
                         [
                             ('0', []),
                         ])

    def test_normalize_category_2(self):
        self.assertEqual(list(normalize('[\d]')),
                         [
                             ('0', []),
                         ])

    def test_normalize_category_3(self):
        self.assertEqual(list(normalize('[^\d]')),
                         [
                             ('!', []),
                         ])

    def test_normalize_category_3a(self):
        self.assertEqual(list(normalize('[^\D]')),
                         [
                             ('0', []),
                         ])

    def test_normalize_category_3b(self):
        self.assertEqual(list(normalize('\D')),
                         [
                             ('x', []),
                         ])

    # def test_normalize_category_4(self):
    #     def bad_call():
    #         return list(normalize('\Za'))
    #
    #     self.assertRaises(NotImplementedError, bad_call)

    def test_normalize_category_5(self):
        self.assertEqual(list(normalize('\s')),
                         [
                             (' ', []),
                         ])

    def test_normalize_category_6(self):
        self.assertEqual(list(normalize('[\s]')),
                         [
                             (' ', []),
                         ])

    def test_normalize_category_7(self):
        self.assertEqual(list(normalize('[^\s]')),
                         [
                             ('!', []),
                         ])

    def test_normalize_backrefs_1(self):
        self.assertEqual(list(normalize('([a-z])/\\1')),
                         [
                             ('%(_0)s/%(_0)s', ['_0']),
                         ])

    def test_normalize_backrefs_named(self):
        self.assertEqual(list(normalize('(?P<a>[a-z]+)/(?P=a)')),
                         [
                             ('%(a)s/%(a)s', ['a']),
                         ])

    def test_normalize_backrefs_nested(self):
        self.assertEqual(list(normalize('(?P<a>(?P<a1>[a-z]+)(?P<a2>\d+))/(?P=a)')),
                         [
                             ('%(a)s/%(a)s', ['a']),
                         ])

    def test_normalize_backrefs_nested2(self):
        self.assertEqual(list(normalize('(?P<a>(?P<a1>[a-z]+)(?P<a2>\d+))/(?P=a2)')),
                         [
                             ('%(a1)s%(a2)s/%(a2)s', ['a1', 'a2']),
                         ])

    def test_normalize_bad_group_name(self):
        def bad_name():
            list(normalize('(?P<_1>group)'))

        self.assertRaises(ValueError, bad_name)

    def test_unique_list(self):
        self.assertEqual(unique_list([9, 1, 2, 1, 1, 3]), [9, 1, 2, 3])

    def test_alternation_1(self):
        self.assertEqual(list(normalize('(first)|(second)')),
                         [
                             ('%(_0)s', ['_0']),
                             ('%(_1)s', ['_1']),
                         ])

    def test_alternation_2(self):
        self.assertEqual(list(normalize('(?P<A>(?P<B>b)|(?P<C>c))')),
                         [
                             ('%(A)s', ['A']),
                             ('%(B)s', ['B']),
                             ('%(C)s', ['C']),
                         ])

    def test_non_matching_group(self):
        self.assertEqual(list(normalize(r"(?:non-capturing)")),
                         [
                             ('non-capturing', []),
                         ])

    def test_any(self):
        self.assertEqual(list(normalize(r"a(.*)")),
                         [
                             ('a%(_0)s', ['_0']),
                         ])

    def test_any_1(self):
        self.assertEqual(list(normalize(r".(.*)")),
                         [
                             ('.%(_0)s', ['_0']),
                         ])

    def test_max_repeat_1(self):
        self.assertEqual(list(normalize(r".*(A)")),
                         [
                             ('%(_0)s', ['_0']),
                         ])

    def test_max_repeat_2(self):
        self.assertEqual(list(normalize(r".+(A)")),
                         [
                             ('.%(_0)s', ['_0']),
                         ])

    def test_max_repeat_3(self):
        self.assertEqual(list(normalize(r"(?:.)+(A)")),
                         [
                             ('.%(_0)s', ['_0']),
                         ])

    def test_max_repeat_4(self):
        self.assertEqual(list(normalize(r"(A)*")),
                         [
                             ('', []),
                             ('%(_0)s', ['_0']),
                         ])

    def test_max_repeat_5(self):
        self.assertEqual(list(normalize(r"(A)+")),
                         [
                             ('%(_0)s', ['_0']),
                         ])

    def test_category_word(self):
        self.assertEqual(list(normalize(r"\w")),
                         [
                             ('x', []),
                         ])

    def test_category_word1(self):
        self.assertEqual(list(normalize(r"\W")),
                         [
                             ('!', []),
                         ])


if __name__ == '__main__':
    unittest.main()