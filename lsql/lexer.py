from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import re

from lsql import expr

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# binding powers:
# IN: 50
# OR: 100
# AND: 200
# =, <>, BETWEEN: 250
# <, <=, >, >=: 260
# ||: 300
# +-: 400
# */: 500
# ^: 600
# (: 700


_MISSING = object()


class Token(object):
    @classmethod
    def from_match(cls, match):
        return cls(
            text=match.group(),
            start=match.start(),
            end=match.end(),
            match=match,
        )

    def __init__(self, text, start, end, match=_MISSING):
        self.text = text
        self.start = start
        self.end = end
        if match == _MISSING:
            self.match = None
        else:
            self.match = match

    def __repr__(self):
        return '{:s}({!r})'.format(self.__class__.__name__, self.text)

    def prefix(self, parser):
        raise NotImplementedError(self._get_not_implemented_message('prefix'))

    def suffix(self, value, parser):
        raise NotImplementedError(self._get_not_implemented_message('suffix'))

    def _get_not_implemented_message(self, method):
        return 'not implemented method .{!s}() in {!r}'.format(method, self)


class KeywordToken(Token):
    pass


# TODO: make it operator token?
class AndToken(KeywordToken):
    right_bp = 200

    def suffix(self, value, parser):
        return expr.AndExpr(value, parser.expr(self.right_bp))


class AsToken(KeywordToken):
    pass


class AscToken(KeywordToken):
    right_bp = 0
    direction = expr.ASC


class BetweenToken(KeywordToken):
    right_bp = 250

    def suffix(self, value, parser):
        first = parser.expr(left_bp=AndToken.right_bp)
        parser.skip(AndToken)
        last = parser.expr()
        return expr.BetweenExpr(value, first, last)


class CaseToken(KeywordToken):
    pass


class ByToken(KeywordToken):
    pass


# TODO: make it operator token?
class ContainsToken(KeywordToken):
    pass


class CountToken(KeywordToken):
    def prefix(self, parser):
        parser.skip(OpeningParenToken)
        if isinstance(parser.token, MulToken):
            arg_expr = expr.LiteralExpr('1')
            parser.advance()
        else:
            arg_expr = parser.expr()
        parser.skip(ClosingParenToken)
        return expr.FunctionExpr('count', [arg_expr])


class DeleteToken(KeywordToken):
    pass


class DescToken(KeywordToken):
    right_bp = 0
    direction = expr.DESC


class DropToken(KeywordToken):
    pass


class ElseToken(KeywordToken):
    pass


class EndToken(KeywordToken):
    pass


class ExistsToken(KeywordToken):
    pass


class FromToken(KeywordToken):
    right_bp = 0


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
    right_bp = 50

    def suffix(self, value, parser):
        parser.skip(OpeningParenToken)
        exprs = get_delimited_exprs(parser, CommaToken)
        parser.skip(ClosingParenToken)
        return expr.InExpr(value, exprs)


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
    right_bp = 0


class NotToken(KeywordToken):
    pass


class NotNullToken(KeywordToken):
    pass


class NullToken(KeywordToken):
    def prefix(self, parser):
        return expr.LiteralExpr(expr.NULL)


class OffsetToken(KeywordToken):
    right_bp = 0


# TODO: make it operator token?
class OrToken(KeywordToken):
    right_bp = 100

    def suffix(self, value, parser):
        return expr.OrExpr(value, parser.expr(self.right_bp))


class OrderToken(KeywordToken):
    right_bp = 0


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
    right_bp = 0


class WhitespaceToken(Token):
    pass


KILO = 1024
MEGA = KILO * 1024
GIGA = MEGA * 1024

# unit -> num of bytes in 1 unit
SIZE_SUFFIXES = {
    'k': KILO,
    'kb': KILO,
    'm': MEGA,
    'mb': MEGA,
    'g': GIGA,
    'gb': GIGA,
}

SECONDS_IN_DAY = 86400
# unit -> num of seconds in 1 unit
TIME_SUFFIXES = {
    'minute': 60,
    'minutes': 60,
    'hour': 3600,
    'hours': 3600,
    'day': SECONDS_IN_DAY,
    'days': SECONDS_IN_DAY,
    'week': SECONDS_IN_DAY * 7,
    'weeks': SECONDS_IN_DAY * 7,
    'month': SECONDS_IN_DAY * 30,
    'months': SECONDS_IN_DAY * 30,
    'year': SECONDS_IN_DAY * 365,
    'years': SECONDS_IN_DAY * 365,
}


def merge_dicts(x, y):
    """
    Merge two dicts into one.
    :type x: dict
    :type y: dict
    :return: merged dictionary
    """
    merged = x.copy()
    merged.update(y)
    return merged


LITERAL_SUFFIXES = merge_dicts(SIZE_SUFFIXES, TIME_SUFFIXES)


class NumberToken(Token):
    @property
    def value(self):
        value = 0
        int_part = self.match.group('int')
        float_part = self.match.group('float')
        exp_part = self.match.group('exp')
        suffix = self.match.group('suffix')
        if int_part:
            value = int(int_part)
        if float_part:
            value += float('0.{}'.format(float_part))
        if exp_part:
            value *= 10 ** float(exp_part)
        if suffix:
            if suffix not in LITERAL_SUFFIXES:
                raise LexerError('unknown suffix: {!r}'.format(suffix), self.start)
            value *= LITERAL_SUFFIXES[suffix]
        return value

    def prefix(self, parser):
        return expr.LiteralExpr(self.value)


class StringToken(Token):
    def prefix(self, parser):
        return expr.LiteralExpr(self.match.group('string'))


class NameToken(Token):
    def prefix(self, parser):
        return expr.NameExpr(self.text)


class OperatorToken(Token):
    function_name = None  # redefine me in subclasses

    # TODO(aershov182): rename `value` to `left`
    def suffix(self, value, parser):
        right = parser.expr(self.right_bp)
        return expr.FunctionExpr(self.function_name, [value, right])


class ConcatToken(OperatorToken):
    right_bp = 300
    function_name = '||'


class DivToken(OperatorToken):
    right_bp = 500
    function_name = '/'


# TODO(aershov182): more consistent bps (multipliers of 100)
class EqToken(OperatorToken):
    right_bp = 250
    function_name = '='


class GtToken(OperatorToken):
    right_bp = 260
    function_name = '>'


class GteToken(OperatorToken):
    right_bp = 260
    function_name = '>='


class LtToken(OperatorToken):
    right_bp = 260
    function_name = '<'


class LteToken(OperatorToken):
    right_bp = 260
    function_name = '<='


class MinusToken(OperatorToken):
    right_bp = 400
    function_name = '-'

    def prefix(self, parser):
        return expr.FunctionExpr('negate', [parser.expr(left_bp=10000)])


class ModuloToken(OperatorToken):
    right_bp = 500
    function_name = '%'


class MulToken(OperatorToken):
    right_bp = 500
    function_name = '*'


class NeToken(OperatorToken):
    right_bp = 260
    function_name = '<>'


class PlusToken(OperatorToken):
    right_bp = 400
    function_name = '+'

    def prefix(self, parser):
        return parser.expr(left_bp=10000)


class PowerToken(OperatorToken):
    right_bp = 600
    function_name = '^'


class SpecialToken(Token):
    pass


class OpeningParenToken(SpecialToken):
    right_bp = 700

    def prefix(self, parser):
        if isinstance(parser.token, ClosingParenToken):
            raise LexerError('expression expected', self.start())
        result = parser.expr()
        if not isinstance(parser.token, ClosingParenToken):
            raise LexerError(') expected', parser.token.start)
        parser.advance()
        return result

    def suffix(self, value, parser):
        if not isinstance(value, expr.NameExpr):
            raise LexerError('expected name, got: {!r}'.format(value), self.start)
        if isinstance(parser.token, ClosingParenToken):
            args = []
        else:
            args = get_delimited_exprs(parser, CommaToken)
        parser.skip(ClosingParenToken)
        return expr.FunctionExpr(value.name, args)


class ClosingParenToken(SpecialToken):
    right_bp = 0


class CommaToken(SpecialToken):
    right_bp = 0


class PeriodToken(SpecialToken):
    pass


class LexerError(Exception):
    def __init__(self, string, pos):
        self.string = string
        self.pos = pos

    def __str__(self):
        substring = self.string[self.pos:self.pos + 20] + '...'
        return "Can't tokenize at position {:d}: {!r}".format(self.pos, substring)


class BeginQueryToken(Token):
    def prefix(self, parser):
        # TODO(aershov182): maybe get rid of this class and move this logic to
        # Parser.parse()
        select_expr = None
        from_expr = None
        where_expr = None
        order_expr = None
        limit_expr = None
        offset_expr = None
        # TODO(aershov182): add .clause() method to tokens
        if isinstance(parser.token, SelectToken):
            parser.advance()
            if isinstance(parser.token, MulToken):
                select_expr = expr.StarExpr()
                parser.advance()
            else:
                select_expr = get_delimited_exprs(parser, CommaToken)
        if isinstance(parser.token, FromToken):
            parser.advance()
            from_expr = parser.expr()
        if isinstance(parser.token, WhereToken):
            parser.advance()
            where_expr = parser.expr()
        if isinstance(parser.token, OrderToken):
            parser.advance()
            parser.skip(ByToken)
            # TODO(aershov182): add ASC/DESC
            order_by_exprs = []
            ob_expr = parser.expr()
            if isinstance(parser.token, (AscToken, DescToken)):
                direction = parser.token.direction
                parser.advance()
            else:
                direction = expr.ASC
            order_by_exprs.append(expr.OneOrderByExpr(ob_expr, direction))
            while isinstance(parser.token, CommaToken):
                parser.advance()
                ob_expr = parser.expr()
                if isinstance(parser.token, (AscToken, DescToken)):
                    direction = parser.token.direction
                    parser.advance()
                else:
                    direction = expr.ASC
                order_by_exprs.append(expr.OneOrderByExpr(ob_expr, direction))
            order_expr = order_by_exprs
        if isinstance(parser.token, LimitToken):
            parser.advance()
            limit_expr = parser.expr()
        if isinstance(parser.token, OffsetToken):
            parser.advance()
            offset_expr = parser.expr()
        parser.expect(EndQueryToken)
        return expr.QueryExpr(
            select_expr=select_expr,
            from_expr=from_expr,
            where_expr=where_expr,
            order_expr=order_expr,
            limit_expr=limit_expr,
            offset_expr=offset_expr,
        )


def get_delimited_exprs(parser, delimiter_token_cls):
    exprs = [parser.expr()]
    while isinstance(parser.token, delimiter_token_cls):
        parser.advance()
        exprs.append(parser.expr())
    return exprs


class EndQueryToken(Token):
    @property
    def right_bp(self):
        return 0


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
                yield token_class.from_match(match)
                start = match.end()
                break
            else:
                raise LexerError(string, start)

    def tokenize(self, string):
        assert isinstance(string, unicode)
        yield BeginQueryToken(string, 0, len(string))
        for token in self.tokenize_with_whitespaces(string):
            if not isinstance(token, WhitespaceToken):
                yield token
        yield EndQueryToken(string, 0, len(string))


def _keyword(s):
    return _regex(r'{}\b'.format(re.escape(s)), re.I)


def _regex(pattern, extra_flags=0):
    return re.compile(pattern, re.UNICODE | extra_flags)


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
        ('count', CountToken),
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
    lexer.add(_regex(r"'(?P<string>(?:[^']|'')*)'"), StringToken)


# [[3].[2]][e[-]10][suffix]
def _add_number_literals(lexer):
    # TODO: check this regexes
    for pattern, number_class in [
        # [2].3[e[-]5][years]
        (r'(?P<int>\d*)\.(?P<float>\d+)(?:e[+-]?(?P<exp>\d+))?(?P<suffix>[^\W\d]+)?\b', NumberToken),
        # 2.[e[-]5][years]
        (r'(?P<int>\d+)\.(?P<float>)(?:(?:e[+-]?(?P<exp>\d+))?(?P<suffix>[^\W\d]+)?\b)?', NumberToken),
        # 2[e[-]5][years]
        (r'(?P<int>\d+)(?P<float>)(?:e[+-]?(?P<exp>\d+))?(?P<suffix>[^\W\d]+)?\b', NumberToken),
    ]:
        lexer.add(_regex(pattern, extra_flags=re.IGNORECASE), number_class)


def _add_whitespace(lexer):
    lexer.add(_regex(r'\s+'), WhitespaceToken)


def _operator(s):
    chars = ''.join(_OPERATOR_CHARS)
    return _regex(r'{}(?![{}])'.format(re.escape(s), re.escape(chars)))


tokenize = _make_default_lexer().tokenize
