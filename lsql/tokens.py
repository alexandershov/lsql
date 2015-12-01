from __future__ import division, print_function, unicode_literals

from collections import namedtuple
import logging

import re

Position = namedtuple('Position', ['string', 'start', 'end'])

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Token(object):
    # TODO: probably __init__ should receive the re.Match object as a single argument
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


# TODO: make it operator token?
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


# TODO: make it operator token?
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


# TODO: make it operator token?
class IcontainsToken(KeywordToken):
    pass


# TODO: make it operator token?
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


# TODO: make it operator token?
class LikeToken(KeywordToken):
    pass


# TODO: make it operator token?
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


# TODO: make it operator token?
class OrToken(KeywordToken):
    pass


class OrderToken(KeywordToken):
    pass


class OuterToken(KeywordToken):
    pass


# TODO: make it operator token?
class RlikeToken(KeywordToken):
    pass


# TODO: make it operator token?
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


class NumberToken(Token):
    pass


class StringToken(Token):
    pass


class NameToken(Token):
    pass


class OperatorToken(Token):
    pass


class ConcatToken(OperatorToken):
    pass


class DivToken(OperatorToken):
    pass


class EqToken(OperatorToken):
    pass


class GtToken(OperatorToken):
    pass


class GteToken(OperatorToken):
    pass


class LtToken(OperatorToken):
    pass


class LteToken(OperatorToken):
    pass


class MinusToken(OperatorToken):
    pass


class ModuloToken(OperatorToken):
    pass


class MulToken(OperatorToken):
    pass


class NeToken(OperatorToken):
    pass


class PlusToken(OperatorToken):
    pass


class PowerToken(OperatorToken):
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
                logger.debug('matching token {!r} with string {!r} at position {:d}'.format(
                    token_class, string, start))
                m = regex.match(string, start)
                if not m:
                    logger.debug('failed token {!r} with string {!r} at position {:d}'.format(
                        token_class, string, start))
                    continue
                logger.debug('success!')
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


# TODO: use _regex in _keyword, _operator, and all _helper_regexes
def _regex(s):
    return re.compile(s, re.U)


# TODO: Parens

def _make_default_lexer():
    lexer = Lexer()
    _add_keywords(lexer)
    _add_operators(lexer)
    _add_string_literals(lexer)
    _add_number_literals(lexer)
    _add_whitespace(lexer)
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


# TODO: create _OPERATOR_CHARS based on _add_operators dynamically
_OPERATOR_CHARS = '|/=><-%*!+^'

def _add_operators(lexer):
    lexer.add(_operator('||'), ConcatToken)
    lexer.add(_operator('/'), DivToken)
    lexer.add(_operator('='), EqToken)
    lexer.add(_operator('>'), GtToken)
    lexer.add(_operator('>='), GteToken)
    lexer.add(_operator('<'), LtToken)
    lexer.add(_operator('<='), LteToken)
    lexer.add(_operator('-'), MinusToken)
    lexer.add(_operator('%'), ModuloToken)
    lexer.add(_operator('*'), MulToken)
    lexer.add(_operator('<>'), NeToken)
    lexer.add(_operator('!='), NeToken)
    lexer.add(_operator('+'), PlusToken)
    lexer.add(_operator('^'), PowerToken)


def _add_string_literals(lexer):
    lexer.add(_regex(r"'([^']|'')*'"), StringToken)


def _add_number_literals(lexer):
    # TODO: check this regexes
    lexer.add(_regex(r'\d+\.?\d*e\d+'), NumberToken)  # 2e10, 2.5e10
    lexer.add(_regex(r'\d+\.?\d*[^\W\d]+'), NumberToken)  # 2year, 2.5year
    lexer.add(_regex(r'\d+\.?\d*'), NumberToken)  # 2, 2.5


def _add_whitespace(lexer):
    lexer.add(re.compile(r'\s+'), WhitespaceToken)


def _operator(s):
    return re.compile(r'{}(?![{}])'.format(re.escape(s), re.escape(_OPERATOR_CHARS)), re.I)


tokenize = _make_default_lexer().tokenize
