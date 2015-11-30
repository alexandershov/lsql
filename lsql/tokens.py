from __future__ import division, print_function, unicode_literals

from collections import namedtuple

import re


Position = namedtuple('Position', ['string', 'start', 'end'])


class Token(object):
    def __init__(self, value, position):
        # TODO: add string, and position in it
        self.value = value
        self.position = position

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.value == other.value:
            return True
        return False

    def __hash__(self):
        return hash((self.__class__, self.value))

    def __repr__(self):
        return '{:s}({!r})'.format(self.__class__.__name__, self.value)


class WhitespaceToken(Token):
    pass


class IntToken(Token):
    pass


class StringToken(Token):
    pass


class KeywordToken(Token):
    def __init__(self, value, position):
        super(KeywordToken, self).__init__(value.upper(), position)


class SelectToken(KeywordToken):
    pass




class NameToken(Token):
    pass


class OperatorToken(Token):
    pass


class LexerError(Exception):
    def __init__(self, string, pos):
        self.string = string
        self.pos = pos

    def __str__(self):
        substring = self.string[self.pos:self.pos + 20] + '...'
        return "Can't tokenize at position {:d}: {!r}".format(self.pos, substring)


class Lexer(object):
    def __init__(self):
        self._rules = []  # [(regex, token_class), ...]

    def add(self, regex, token_class):
        self._rules.append((regex, token_class))

    def tokenize_with_whitespaces(self, string):
        start = 0
        while start < len(string):
            for regex, token_class in self._rules:
                m = regex.match(string, start)
                if not m:
                    continue
                position = Position(string, start, m.end())
                yield token_class(string[start:m.end()], position)
                start = m.end()
                break
            else:
                raise LexerError(string, start)

    def tokenize(self, string):
        assert isinstance(string, unicode)
        for token in self.tokenize_with_whitespaces(string):
            if not isinstance(token, WhitespaceToken):
                yield token


def _keyword(s):
    return re.compile(r'{}\b'.format(re.escape(s)), re.I | re.U)


# TODO: Parens

def _make_default_lexer():
    lexer = Lexer()
    lexer.add(_keyword('select'), SelectToken)
    lexer.add(_keyword('and'), OperatorToken)
    lexer.add(re.compile(r'\d+\w*', re.I | re.U), IntToken)
    lexer.add(re.compile(r'\s+'), WhitespaceToken)
    lexer.add(re.compile(r'\w+'), NameToken)
    return lexer


tokenize = _make_default_lexer().tokenize
