import unittest


class Token:
    OPEN_PAREN = ord('(')
    CLOSE_PAREN = ord(')')


class Node:
    def __init__(self, pattern_iterator):
        self.quantifier = Node.Quantifier(pattern_iterator)

    @classmethod
    def parse(cls, pi):
        raise NotImplementedError()

    def render(self, context):
        raise NotImplementedError()

    class Quantifier:
        """Parses regexp quantifiers for any element.

        The quantifier is represented by the minimum number of repetitions
        and the possibility to omit the element altogether

        Supported quantifiers:
        ?
        *
        *?
        +
        +?
        {a}
        {a,}
        {,b}
        {a,b}

        Pseudo quantifiers:
        {a}?
        {a,}?
        {,b}?
        {a,b}?
        """

        def __init__(self, pattern_iterator):
            self.optional, self.min_count = self.parse(pattern_iterator)

        @classmethod
        def parse(cls, pi):
            ch = pi.peek()
            if not ch:
                return False, 1

            if ch in '?':
                pi.next()
                return True, 1
            elif ch == '+':
                pi.next()
                if pi.peek() == '?':  # non-greedy foo+? match
                    pi.next()
                return False, 1
            elif ch == '*':
                pi.next()
                if pi.peek() == '?':  # non-greedy foo*? match
                    pi.next()
                return True, 1
            elif ch == '{':
                digits = ['0']
                min_count = None
                pi.next()
                while True:
                    ch = pi.next()
                    if ch == '}':
                        if min_count is None:
                            min_count = int(''.join(digits))
                        break
                    elif ch == ',':
                        min_count = int(''.join(digits))
                    else:
                        assert ch.isdigit()
                        digits.append(ch)
                if pi.peek() == '?':
                    pi.next()
                    return True, min_count
                return False, min_count

        def render(self, text):
            if self.optional:
                yield ''
            yield text * self.min_count


class TextNode(Node):
    def __init__(self, pattern_iterator):
        self.text = self.parse(pattern_iterator)
        super().__init__(pattern_iterator)

    @classmethod
    def is_regex_special_char(cls, c):
        return c in '^$[\\?*+|{('

    @classmethod
    def parse(cls, pi):
        text = []
        try:
            while not cls.is_regex_special_char(pi.peek()):
                text.append(pi.next())
        except StopIteration:
            pass
        return "".join(text)

    def render(self, context):
        if self.quantifier.optional:
            yield '', []
        else:
            for i in self.quantifier.render(self.text):
                yield i, []


class GroupNode(Node):
    def __init__(self, pattern_iterator):
        super().__init__(pattern_iterator)

    @classmethod
    def parse(cls, pi):
        name = []
        while True:
            ch = pi.next()
            if ch == '>':
                break
            name.append(ch)

        parenth


class GroupReferenceNode(Node):
    pass


class RegexLexer:
    ESCAPE_MAPPINGS = {
        "A": None,
        "b": None,
        "B": None,
        "d": "0",
        "D": "x",
        "s": " ",
        "S": "x",
        "w": "x",
        "W": "!",
        "Z": None,
    }

    def __init__(self, pattern):
        self.it = iter(pattern)

    def __iter__(self):
        def _next():
            while True:
                ch = next(self.it)
                if ch == '\\':
                    ch = next(self.it)
                    yield self.ESCAPE_MAPPINGS.get(ch, ch)
                elif ch == '(':
                    yield Token.OPEN_PAREN
                elif ch == ')':
                    yield Token.CLOSE_PAREN
                elif ch == '[':
                    ch = next(self.it)
                    if ch in '^[':
                        raise NotImplementedError('Please do not use negations or named character classes')
                    elif ch == '\\':
                        ch = next(self.it)
                    first_found = ch
                    while True:
                        ch = next(self.it)
                        if ch == ']':
                            break
                        elif ch == '\\':
                            next(self.it)
                    yield first_found
                elif ch in '^$':
                    pass
                else:
                    yield ch
        return _next()


class PeekableIterator:
    """
    Iterator which allows to get one next element without consuming it.
    """
    _sentinel = object()
    peeked = _sentinel

    def __init__(self, it):
        self.it = iter(it)

    def __iter__(self):
        return self

    def next(self):
        if self.peeked is self._sentinel:
            return next(self.it)
        else:
            next_value = self.peeked
            self.peeked = self._sentinel
            return next_value

    def peek(self):
        if self.peeked is self._sentinel:
            self.peeked = next(self.it)
        return self.peeked


class PeekableStringIterator(PeekableIterator):
    def peek(self):
        try:
            return super().peek()
        except StopIteration:
            return ''


class FlagNode(Node):
    def __init__(self, pattern_iterator):
        self.parse(pattern_iterator)
        # not running super() here, as we don't want to parse quantifier for flag nodes

    @classmethod
    def parse(cls, pi):
        while pi.next() != ')':
            pass

    def render(self, context):
        yield '', []


class UnnamedGroup(GroupNode):
    pass


class NoncapturingGroup(GroupNode):
    pass


def _parse_regex(pi):
    ch = pi.peek()

    if ch == '(':
        #  Groups
        pi.next()
        if pi.peek() == '?':
            # Named Group or GroupReference
            pi.next()
            ch = pi.peek()
            if ch in ('a', 'i', 'L', 'm', 's', 'u', 'x'):
                FlagNode(pi)
            elif ch == ':':
                pi.next()
                yield NoncapturingGroup(pi)
            elif ch == 'P':
                pi.next()
                ch = pi.next()
                if ch == '=':
                    yield GroupReferenceNode(pi)
                else:
                    assert ch == '<'
                    yield GroupNode(pi)

        else:
            # Unnamed Group
            UnnamedGroup()

    elif ch == '[':
        #  Classes
        pass
    elif ch == '$':
        return
    elif ch == '|':
        raise NotImplementedError('Alternations are not supported.')
    else:
        yield TextNode(pi)


def parse_regex(pattern):
    pi = PeekableStringIterator(pattern)

    _parse_regex(pi)


class RegexLexerTestCase(unittest.TestCase):

    def test_1(self):
        rl = RegexLexer('test')
        self.assertEqual(list(rl), list('test'))

    def test_2(self):
        rl = RegexLexer('test[abc]')
        self.assertEqual(list(rl), list('testa'))

    def test_escape1(self):
        rl = RegexLexer('test\\d')
        self.assertEqual(list(rl), list('test0'))

    def test_escape1_5(self):
        rl = RegexLexer('test\\\\')
        self.assertEqual(list(rl), list('test\\'))

    def test_escape2(self):
        rl = RegexLexer('test[\\d]')
        self.assertEqual(list(rl), list('testd'))

    def test_escape3(self):
        rl = RegexLexer('test[\\\\]')
        self.assertEqual(list(rl), list('test\\'))

    def test_escape4(self):
        rl = RegexLexer('test[]]')
        self.assertEqual(list(rl), list('test]'))

    def test_3(self):
        rl = RegexLexer('test(abc)')
        self.assertEqual(list(rl), list('test') + [Token.OPEN_PAREN] + list('abc') + [Token.CLOSE_PAREN])


class TextNodeTestCase(unittest.TestCase):
    def test_plain_text(self):
        pi = PeekableStringIterator('test')
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_question_mark(self):
        pi = PeekableStringIterator('test?')
        self.assertEqual(TextNode.parse(pi), 'test')


    def test_escape(self):
        pi = PeekableStringIterator('test\\(')
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_parenthesis(self):
        pi = PeekableStringIterator('test(')
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_brace(self):
        pi = PeekableStringIterator('test{')
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_plus(self):
        pi = PeekableStringIterator('test+')
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_star(self):
        pi = PeekableStringIterator('test*')
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_dollar(self):
        pi = PeekableStringIterator('test$')
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_node(self):
        pi = PeekableStringIterator('test{3}')
        node = TextNode(pi)
        self.assertEqual(node.text, 'test')
        self.assertEqual(node.quantifier.min_count, 3)
        self.assertEqual(node.quantifier.optional, False)


class PeekableStringIteratorTestCase(unittest.TestCase):
    def test_peakable_iterator(self):
        a = PeekableStringIterator(range(1000))
        self.assertEqual(a.next(), 0)
        self.assertEqual(a.peek(), 1)
        self.assertEqual(a.next(), 1)
        self.assertEqual(a.peek(), 2)
        self.assertEqual(a.peek(), 2)
        self.assertEqual(a.next(), 2)
        self.assertEqual(a.next(), 3)


class NodeQuantifierTestCase(unittest.TestCase):
    def test_empty(self):
        pi = PeekableStringIterator('')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, False)
        self.assertRaises(StopIteration, pi.next)

    def test_optional(self):
        pi = PeekableStringIterator('?test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')

    def test_end_of_string(self):
        pi = PeekableStringIterator('?')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, True)
        self.assertRaises(StopIteration, pi.next)


    def test_plus(self):
        pi = PeekableStringIterator('+test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')

    def test_plus_nongreedy(self):
        pi = PeekableStringIterator('+?test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')

    def test_star(self):
        pi = PeekableStringIterator('*test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


    def test_star_nongreedy(self):
        pi = PeekableStringIterator('*?test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


    def test_repeat(self):
        pi = PeekableStringIterator('{3}test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')

    def test_repeat_from(self):
        pi = PeekableStringIterator('{3,}test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')


    def test_repeat_from_until(self):
        pi = PeekableStringIterator('{3,5}test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')


    def test_repeat_until(self):
        pi = PeekableStringIterator('{,5}test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 0)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')


    def test_repeat_optional(self):
        pi = PeekableStringIterator('{8}?test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 8)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')

    def test_repeat_from_optional(self):
        pi = PeekableStringIterator('{3,}?test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


    def test_repeat_from_until_optional(self):
        pi = PeekableStringIterator('{3,5}?test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


    def test_repeat_until_optional(self):
        pi = PeekableStringIterator('{,5}?test')
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 0)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


if __name__ == "__main__":
    unittest.main()
