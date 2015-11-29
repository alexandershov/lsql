from __future__ import division, print_function, unicode_literals

import re


class Token(object):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.value == other.value:
            return True
        return False

    # TODO: add __hash__

    def __repr__(self):
        return '{:s}({!r})'.format(self.__class__.__name__, self.value)


class WhitespaceToken(Token):
    pass


class IntToken(Token):
    pass


class StringToken(Token):
    pass


# TODO: should case-insensitive __eq__
class KeywordToken(Token):
    pass


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

    def tokenize(self, string):
        pos = 0
        while pos < len(string):
            for regex, token_class in self._rules:
                m = regex.match(string, pos)
                if not m:
                    continue
                if token_class is not WhitespaceToken:
                    yield token_class(string[pos:m.end()])
                pos = m.end()
                break
            else:
                raise LexerError(string, pos)

# TODO: Parens

# TODO: move rules to constructor
_lexer = Lexer()
_lexer.add(re.compile(r'select\b', re.I | re.U), SelectToken)
_lexer.add(re.compile(r'\d+\w*', re.I | re.U), IntToken)
_lexer.add(re.compile(r'\s+'), WhitespaceToken)
_lexer.add(re.compile(r'\w+'), NameToken)
tokenize = _lexer.tokenize
