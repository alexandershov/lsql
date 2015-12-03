from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import re

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class Token(object):
    def __init__(self, match):
        self._match = match
        self.text = match.group()
        self.start = match.start()
        self.end = match.end()

    def __repr__(self):
        return '{:s}({!r})'.format(self.__class__.__name__, self.text)


class KeywordToken(Token):
    pass


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


class SpecialToken(Token):
    pass


class OpeningParenToken(SpecialToken):
    pass


class ClosingParenToken(SpecialToken):
    pass


class CommaToken(SpecialToken):
    pass


class PeriodToken(SpecialToken):
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
                logger.debug('matching regex {!r} with string {!r} at position {:d}'.format(
                    regex.pattern, string, start))
                match = regex.match(string, start)
                if not match:
                    logger.debug('failed')
                    continue
                logger.debug('success!')
                yield token_class(match)
                start = match.end()
                break
            else:
                raise LexerError(string, start)

    def tokenize(self, string):
        assert isinstance(string, unicode)
        for token in self.tokenize_with_whitespaces(string):
            if not isinstance(token, WhitespaceToken):
                yield token


def _keyword(s):
    return _regex(r'{}\b'.format(re.escape(s)), re.I)


def _regex(pattern, extra_flags=0):
    return re.compile(pattern, re.U | extra_flags)


def _make_default_lexer():
    lexer = Lexer()
    _add_keywords(lexer)
    _add_names(lexer)
    _add_operators(lexer)
    _add_string_literals(lexer)
    _add_number_literals(lexer)
    _add_whitespace(lexer)
    _add_special(lexer)  # special should go after number_literals because of '.2'
    return lexer


def _add_special(lexer):
    for pattern, special_class in [
        (r'\)', ClosingParenToken),
        (r'\,', CommaToken),
        (r'\(', OpeningParenToken),
        (r'\.', PeriodToken)
    ]:
        lexer.add(_regex(pattern), special_class)


def _add_keywords(lexer):
    for pattern, keyword_class in [
        ('and', AndToken),
        ('as', AsToken),
        ('asc', AscToken),
        ('between', BetweenToken),
        ('by', ByToken),
        ('case', CaseToken),
        ('contains', ContainsToken),
        ('delete', DeleteToken),
        ('desc', DescToken),
        ('drop', DropToken),
        ('else', ElseToken),
        ('end', EndToken),
        ('exists', ExistsToken),
        ('from', FromToken),
        ('group', GroupToken),
        ('having', HavingToken),
        ('icontains', IcontainsToken),
        ('ilike', IlikeToken),
        ('in', InToken),
        ('is', IsToken),
        ('isnull', IsNullToken),
        ('join', JoinToken),
        ('left', LeftToken),
        ('like', LikeToken),
        ('like_regex', LikeRegexToken),
        ('limit', LimitToken),
        ('not', NotToken),
        ('notnull', NotNullToken),
        ('null', NullToken),
        ('offset', OffsetToken),
        ('or', OrToken),
        ('order', OrderToken),
        ('outer', OuterToken),
        ('rilike', RilikeToken),
        ('rlike', RlikeToken),
        ('select', SelectToken),
        ('then', ThenToken),
        ('update', UpdateToken),
        ('where', WhereToken),
    ]:
        lexer.add(_keyword(pattern), keyword_class)


def _add_names(lexer):
    lexer.add(_regex(r'[^\W\d]\w*'), NameToken)

# populated in _add_operators
_OPERATOR_CHARS = set()


def _add_operators(lexer):
    pattern_classes = [
        ('||', ConcatToken),
        ('/', DivToken),
        ('=', EqToken),
        ('>', GtToken),
        ('>=', GteToken),
        ('<', LtToken),
        ('<=', LteToken),
        ('-', MinusToken),
        ('%', ModuloToken),
        ('*', MulToken),
        ('<>', NeToken),
        ('!=', NeToken),
        ('+', PlusToken),
        ('^', PowerToken),
    ]
    for pattern, _ in pattern_classes:
        _OPERATOR_CHARS.update(pattern)
    for pattern, operator_class in pattern_classes:
        lexer.add(_operator(pattern), operator_class)


def _add_string_literals(lexer):
    lexer.add(_regex(r"'([^']|'')*'"), StringToken)

# [[3].[2]][e10][suffix]
def _add_number_literals(lexer):
    # TODO: check this regexes
    for pattern, number_class in [
        # [2].3[e5][years]
        (r'\d*\.\d+(?:e\d+)?(?:[^\W\d]+)?\b', NumberToken),
        # 2.[e5][years]
        (r'\d+\.(?:(?:e\d+)?(?:[^\W\d]+)?\b)?', NumberToken),
        # 2[e5][years]
        (r'\d+(?:e\d+)?(?:[^\W\d]+)?\b', NumberToken),
    ]:
        lexer.add(_regex(pattern), number_class)


def _add_whitespace(lexer):
    lexer.add(_regex(r'\s+'), WhitespaceToken)


def _operator(s):
    chars = ''.join(_OPERATOR_CHARS)
    return _regex(r'{}(?![{}])'.format(re.escape(s), re.escape(chars)))


tokenize = _make_default_lexer().tokenize
