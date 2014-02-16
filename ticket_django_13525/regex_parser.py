import unittest


class Node:
    def __init__(self, pattern_iterator):
        self.quantifier = Node.Quantifier(pattern_iterator)

    @classmethod
    def parse(cls, pi):
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
            try:
                ch = pi.peek()
            except StopIteration:
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


class GroupNode(Node):
    pass


class GroupReferenceNode(Node):
    pass


class PeekableIterator:
    """
    Iterator which allows to get one next element without consuming it.
    """
    _sentinel = object()
    peeked = _sentinel

    def __init__(self, it):
        self.it = it

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


def parse_regex(pattern):
    pass


class TextNodeTestCase(unittest.TestCase):

    def test_plain_text(self):
        pi = PeekableIterator(iter('test'))
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_question_mark(self):
        pi = PeekableIterator(iter('test?'))
        self.assertEqual(TextNode.parse(pi), 'test')


    def test_escape(self):
        pi = PeekableIterator(iter('test\\('))
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_parenthesis(self):
        pi = PeekableIterator(iter('test('))
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_brace(self):
        pi = PeekableIterator(iter('test{'))
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_plus(self):
        pi = PeekableIterator(iter('test+'))
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_star(self):
        pi = PeekableIterator(iter('test*'))
        self.assertEqual(TextNode.parse(pi), 'test')

    def test_dollar(self):
        pi = PeekableIterator(iter('test$'))
        self.assertEqual(TextNode.parse(pi), 'test')


class PeekableIteratorTestCase(unittest.TestCase):

    def test_peakable_iterator(self):
        a = PeekableIterator(iter(range(1000)))
        self.assertEqual(a.next(), 0)
        self.assertEqual(a.peek(), 1)
        self.assertEqual(a.next(), 1)
        self.assertEqual(a.peek(), 2)
        self.assertEqual(a.peek(), 2)
        self.assertEqual(a.next(), 2)
        self.assertEqual(a.next(), 3)


class NodeQuantifierTestCase(unittest.TestCase):
    def test_optional(self):
        pi = PeekableIterator(iter('?test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')

    def test_end_of_string(self):
        pi = PeekableIterator(iter('?'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, True)
        self.assertRaises(StopIteration, pi.next)


    def test_plus(self):
        pi = PeekableIterator(iter('+test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')

    def test_plus_nongreedy(self):
        pi = PeekableIterator(iter('+?test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')

    def test_star(self):
        pi = PeekableIterator(iter('*test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


    def test_star_nongreedy(self):
        pi = PeekableIterator(iter('*?test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 1)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


    def test_repeat(self):
        pi = PeekableIterator(iter('{3}test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')

    def test_repeat_from(self):
        pi = PeekableIterator(iter('{3,}test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')


    def test_repeat_from_until(self):
        pi = PeekableIterator(iter('{3,5}test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')


    def test_repeat_until(self):
        pi = PeekableIterator(iter('{,5}test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 0)
        self.assertEqual(q.optional, False)
        self.assertEqual(pi.next(), 't')


    def test_repeat_optional(self):
        pi = PeekableIterator(iter('{8}?test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 8)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')

    def test_repeat_from_optional(self):
        pi = PeekableIterator(iter('{3,}?test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


    def test_repeat_from_until_optional(self):
        pi = PeekableIterator(iter('{3,5}?test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 3)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


    def test_repeat_until_optional(self):
        pi = PeekableIterator(iter('{,5}?test'))
        q = Node.Quantifier(pi)
        self.assertEqual(q.min_count, 0)
        self.assertEqual(q.optional, True)
        self.assertEqual(pi.next(), 't')


if __name__ == "__main__":
    unittest.main()
