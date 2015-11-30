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


class KeywordToken(Token):
    def __init__(self, value, position):
        super(KeywordToken, self).__init__(value.upper(), position)


class AndToken(KeywordToken):
    pass


class AsToken(KeywordToken):
    pass


class AscToken(KeywordToken):
    pass


class BetweenToken(KeywordToken):
    pass


class CaseToken(KeywordToken):
    pass


class ByToken(KeywordToken):
    pass


class ContainsToken(KeywordToken):
    pass


class DeleteToken(KeywordToken):
    pass


class DescToken(KeywordToken):
    pass


class DropToken(KeywordToken):
    pass


class ElseToken(KeywordToken):
    pass


class EndToken(KeywordToken):
    pass


class ExistsToken(KeywordToken):
    pass


class FromToken(KeywordToken):
    pass


class GroupToken(KeywordToken):
    pass


class HavingToken(KeywordToken):
    pass


class IcontainsToken(KeywordToken):
    pass


class IlikeToken(KeywordToken):
    pass


class InToken(KeywordToken):
    pass


class IsToken(KeywordToken):
    pass


class IsNullToken(KeywordToken):
    pass


class JoinToken(KeywordToken):
    pass


class LeftToken(KeywordToken):
    pass


class LikeToken(KeywordToken):
    pass


class LikeRegexToken(KeywordToken):
    pass


class LimitToken(KeywordToken):
    pass


class NotToken(KeywordToken):
    pass


class NotNullToken(KeywordToken):
    pass


class NullToken(KeywordToken):
    pass


class OffsetToken(KeywordToken):
    pass


class OrToken(KeywordToken):
    pass


class OrderToken(KeywordToken):
    pass


class OuterToken(KeywordToken):
    pass


class RlikeToken(KeywordToken):
    pass


class RilikeToken(KeywordToken):
    pass


class SelectToken(KeywordToken):
    pass


class ThenToken(KeywordToken):
    pass


class UpdateToken(KeywordToken):
    pass


class WhereToken(KeywordToken):
    pass


class WhitespaceToken(Token):
    pass


class IntToken(Token):
    pass


class StringToken(Token):
    pass


class NameToken(Token):
    pass


class OperatorToken(Token):
    pass


class DivToken(OperatorToken):
    pass


class MinusToken(OperatorToken):
    pass


class MulToken(OperatorToken):
    pass


class PlusToken(OperatorToken):
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
    _add_keywords(lexer)
    _add_operators(lexer)
    return lexer


def _add_keywords(lexer):
    lexer.add(_keyword('and'), AndToken)
    lexer.add(_keyword('as'), AsToken)
    lexer.add(_keyword('asc'), AscToken)
    lexer.add(_keyword('between'), BetweenToken)
    lexer.add(_keyword('by'), ByToken)
    lexer.add(_keyword('case'), CaseToken)
    lexer.add(_keyword('contains'), ContainsToken)
    lexer.add(_keyword('delete'), DeleteToken)
    lexer.add(_keyword('desc'), DescToken)
    lexer.add(_keyword('drop'), DropToken)
    lexer.add(_keyword('else'), ElseToken)
    lexer.add(_keyword('end'), EndToken)
    lexer.add(_keyword('exists'), ExistsToken)
    lexer.add(_keyword('from'), FromToken)
    lexer.add(_keyword('group'), GroupToken)
    lexer.add(_keyword('having'), HavingToken)
    lexer.add(_keyword('icontains'), IcontainsToken)
    lexer.add(_keyword('ilike'), IlikeToken)
    lexer.add(_keyword('in'), InToken)
    lexer.add(_keyword('is'), IsToken)
    lexer.add(_keyword('isnull'), IsNullToken)
    lexer.add(_keyword('join'), JoinToken)
    lexer.add(_keyword('left'), LeftToken)
    lexer.add(_keyword('like'), LikeToken)
    lexer.add(_keyword('like_regex'), LikeRegexToken)
    lexer.add(_keyword('limit'), LimitToken)
    lexer.add(_keyword('not'), NotToken)
    lexer.add(_keyword('notnull'), NotNullToken)
    lexer.add(_keyword('null'), NullToken)
    lexer.add(_keyword('offset'), OffsetToken)
    lexer.add(_keyword('or'), OrToken)
    lexer.add(_keyword('order'), OrderToken)
    lexer.add(_keyword('outer'), OuterToken)
    lexer.add(_keyword('rilike'), RilikeToken)
    lexer.add(_keyword('rlike'), RlikeToken)
    lexer.add(_keyword('select'), SelectToken)
    lexer.add(_keyword('then'), ThenToken)
    lexer.add(_keyword('update'), UpdateToken)
    lexer.add(_keyword('where'), WhereToken)
    lexer.add(re.compile(r'\d+\w*', re.I | re.U), IntToken)
    lexer.add(re.compile(r'\s+'), WhitespaceToken)
    lexer.add(re.compile(r'\w+'), NameToken)


def _add_operators(lexer):
    lexer.add(_operator(r'/'), DivToken)
    lexer.add(_operator(r'-'), MinusToken)
    lexer.add(_operator(r'*'), MulToken)
    lexer.add(_operator(r'+'), PlusToken)


def _operator(s):
    return re.compile(re.escape(s), re.I)


tokenize = _make_default_lexer().tokenize
