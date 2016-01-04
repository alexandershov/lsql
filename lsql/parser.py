from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial
import logging
import re

from lsql import expr
from lsql.errors import LsqlError

logger = logging.getLogger(__name__)

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


def _merge_dicts(x, y):
    """
    Merge two dicts into one.
    :type x: dict
    :type y: dict
    :return: merged dictionary
    """
    merged = x.copy()
    merged.update(y)
    return merged


LITERAL_SUFFIXES = _merge_dicts(SIZE_SUFFIXES, TIME_SUFFIXES)


class LexerError(LsqlError):
    def __init__(self, string, pos):
        self.string = string
        self.pos = pos

    def __str__(self):
        substring = self.string[self.pos:self.pos + 20] + '...'
        return "Can't tokenize at position {:d}: {!r}".format(self.pos, substring)


class ParserError(LsqlError):
    pass


class UnexpectedTokenError(ParserError):
    def __init__(self, expected_token_class, actual_token):
        self.expected_token_class = expected_token_class
        self.actual_token = actual_token


class UnexpectedEnd(ParserError):
    pass


class UnknownLiteralSuffixError(ParserError):
    def __init__(self, suffix, token):
        self.suffix = suffix
        self.token = token

    @property
    def known_suffixes(self):
        return LITERAL_SUFFIXES.keys()


class Parser(object):
    def __init__(self, tokens):
        self._tokens = list(tokens)
        self._index = 0

    def expect(self, expected_token_class):
        if not isinstance(self.token, expected_token_class):
            raise UnexpectedTokenError(expected_token_class, self.token)

    def skip(self, expected_token_class):
        self.expect(expected_token_class)
        self.advance()

    def advance(self):
        self._check_bounds(self._index + 1)
        self._index += 1

    def _check_bounds(self, index):
        if index >= len(self._tokens):
            raise UnexpectedEnd('unexpected end of query')

    def peek(self):
        self._check_bounds(self._index + 1)
        return self._tokens[self._index + 1]

    @property
    def token(self):
        return self._tokens[self._index]

    def parse(self):
        # order of _get_clause calls is important, because order of clauses is important in SQL
        select_expr = self._get_clause(SelectToken)
        from_expr = self._get_clause(FromToken)
        where_expr = self._get_clause(WhereToken)
        order_expr = self._get_clause(OrderToken)
        limit_expr = self._get_clause(LimitToken)
        offset_expr = self._get_clause(OffsetToken)

        self.expect(EndQueryToken)

        return expr.QueryExpr(
            select_expr=select_expr,
            from_expr=from_expr,
            where_expr=where_expr,
            order_expr=order_expr,
            limit_expr=limit_expr,
            offset_expr=offset_expr,
        )

    def _get_clause(self, token_class, default=None):
        if isinstance(self.token, token_class):
            token = self.token
            self.advance()
            return token.clause(self)
        return default

    def expr(self, left_bp=0):
        token = self.token
        self.advance()
        left = token.prefix(self)
        while self.token.right_bp > left_bp:
            token = self.token
            self.advance()
            left = token.suffix(left, self)
        return left

    def parse_delimited_exprs(self, delimiter_token_cls, parse_fn=None):
        if parse_fn is None:
            parse_fn = self.expr
        exprs = [parse_fn()]
        while isinstance(self.token, delimiter_token_cls):
            self.advance()
            exprs.append(parse_fn())
        return exprs


def parse(tokens):
    return Parser(tokens).parse()


class Token(object):
    def __init__(self, match):
        """
        :param match: Regex match object.
        :return:
        """
        assert match is not None
        self.match = match

    @property
    def text(self):
        return self.match.group()

    @property
    def start(self):
        """Starting position (inclusive) of the token in the string."""
        return self.match.start()

    @property
    def end(self):
        """Ending position (non-inclusive) of the token in the string."""
        return self.match.end()

    @property
    def left_bp(self):
        cls = self.__class__
        try:
            return LEFT_BINDING_POWERS[cls]
        except KeyError:
            raise NotImplementedError('please add {} to LEFT_BINDING_POWERS'.format(cls.__name__))

    @property
    def right_bp(self):
        cls = self.__class__
        try:
            return RIGHT_BINDING_POWERS[cls]
        except KeyError:
            raise NotImplementedError('please add {} to RIGHT_BINDING_POWERS'.format(cls.__name__))

    def prefix(self, parser):
        """
        Called when token is encountered in prefix position.
        :type parser: lsql.parser.Parser
        :rtype: lsql.expr.Expr

        Examples (^ means current token position):

        * In this case we call MinusToken().prefix(parser):
          -3
          ^

        * In this case we call NumberToken(4).prefix(parser):
          2 - 4
              ^
        """
        raise NotImplementedError(self._get_not_implemented_message('prefix'))

    def suffix(self, left, parser):
        """
        Called when token is encountered in suffix position.

        :param left: Expression to the left of the token.
        :type left: lsql.expr.Expr
        :type parser: lsql.parser.Parser
        :rtype: lsql.expr.Expr

        Example (^ means current token position):

        * In this case we call MinusToken().suffix(LiteralExpr(2), parser):
          2 - 4
            ^
        """
        raise NotImplementedError(self._get_not_implemented_message('suffix'))

    def clause(self, parser):
        """
        Called in special cases. For example Parser.parse() will call .clause() on
        SelectToken, FromToken, WhereToken etc.

        :type parser: lsql.parser.Parser
        :rtype: lsql.expr.Expr
        """
        raise NotImplementedError(self._get_not_implemented_message('clause'))

    def _get_not_implemented_message(self, method):
        return 'not implemented method .{!s}() in {!r}'.format(method, self)

    def __repr__(self):
        return '{:s}(text={!r}, start={!r}, end={!r})'.format(
            self.__class__.__name__, self.text, self.start, self.end
        )


class KeywordToken(Token):
    """Base class for keyword tokens."""


class AsToken(KeywordToken):
    pass  # not implemented yet


class AscToken(KeywordToken):
    direction = expr.ASC


class DescToken(KeywordToken):
    direction = expr.DESC


class BetweenToken(KeywordToken):
    def suffix(self, left, parser):
        first = parser.expr(left_bp=self.right_bp)
        parser.skip(AndToken)
        last = parser.expr()
        return expr.BetweenExpr(left, first, last)


class CaseToken(KeywordToken):
    pass  # not implemented yet


class ByToken(KeywordToken):
    pass


class ContainsToken(KeywordToken):
    pass  # not implemented yet


class CountToken(KeywordToken):
    pass  # not implemented yet


class DeleteToken(KeywordToken):
    pass  # not implemented yet


class DropToken(KeywordToken):
    pass  # not implemented yet


class ElseToken(KeywordToken):
    pass  # not implemented yet


class EndToken(KeywordToken):
    pass  # not implemented yet


class ExistsToken(KeywordToken):
    pass  # not implemented yet


class FromToken(KeywordToken):
    def clause(self, parser):
        return parser.expr()


class GroupToken(KeywordToken):
    pass  # not implemented yet


class HavingToken(KeywordToken):
    pass  # not implemented yet


class IsToken(KeywordToken):
    pass  # not implemented yet


class IsNullToken(KeywordToken):
    pass  # not implemented yet


class JoinToken(KeywordToken):
    pass  # not implemented yet


class LeftToken(KeywordToken):
    pass  # not implemented yet


class AndToken(KeywordToken):
    def suffix(self, left, parser):
        return expr.AndExpr(left, parser.expr(self.right_bp))


class OperatorToken(Token):
    operator_name = None  # should be redefined in subclasses

    def suffix(self, left, parser):
        right = parser.expr(self.right_bp)
        return expr.FunctionExpr(self.operator_name, [left, right])


class InToken(OperatorToken):
    operator_name = 'in'

    def suffix(self, left, parser):
        parser.skip(OpeningParenToken)
        exprs = parser.parse_delimited_exprs(CommaToken)
        parser.skip(ClosingParenToken)
        return expr.FunctionExpr(self.operator_name, [left, expr.ArrayExpr(exprs)])


class LikeToken(OperatorToken):
    pass  # not implemented yet


# alias for rlike
class LikeRegexToken(OperatorToken):
    pass  # not implemented yet


class IcontainsToken(OperatorToken):
    pass  # not implemented yet


class IlikeToken(OperatorToken):
    pass  # not implemented yet


class LimitToken(KeywordToken):
    def clause(self, parser):
        return parser.expr()


class NotToken(OperatorToken):
    pass  # not implemented yet


class NotNullToken(KeywordToken):
    pass  # not implemented yet


class NullToken(KeywordToken):
    def prefix(self, parser):
        return expr.LiteralExpr(expr.NULL)


class OffsetToken(KeywordToken):
    def clause(self, parser):
        return parser.expr()


class OrToken(KeywordToken):
    def suffix(self, left, parser):
        return expr.OrExpr(left, parser.expr(self.right_bp))


class OrderToken(KeywordToken):
    def clause(self, parser):
        parser.skip(ByToken)
        sub_exprs = parser.parse_delimited_exprs(
            CommaToken,
            partial(_parse_one_order_by_clause, parser=parser)
        )
        return expr.ListExpr(sub_exprs)


def _parse_one_order_by_clause(parser):
    part_expr = parser.expr()
    if isinstance(parser.token, (AscToken, DescToken)):
        direction = parser.token.direction
        parser.advance()
    else:
        direction = expr.ASC
    return expr.OrderByPartExpr(part_expr, direction)


class OuterToken(KeywordToken):
    pass  # not implemented yet


class RlikeToken(KeywordToken):
    pass  # not implemented yet


class RilikeToken(KeywordToken):
    pass  # not implemented yet


class SelectToken(KeywordToken):
    def clause(self, parser):
        if isinstance(parser.token, MulToken):
            select_expr = expr.SelectStarExpr()
            parser.advance()
        else:
            select_expr = expr.ListExpr(parser.parse_delimited_exprs(CommaToken))
        return select_expr


class ThenToken(KeywordToken):
    pass  # not implemented yet


class UpdateToken(KeywordToken):
    pass  # not implemented yet


class WhereToken(KeywordToken):
    def clause(self, parser):
        return parser.expr()


class WhitespaceToken(Token):
    pass


class NumberToken(Token):
    @property
    def value(self):
        result = 0
        # self.match is a match of some regex from _add_number_literals
        int_part = self.match.group('int')
        float_part = self.match.group('float')
        exp_part = self.match.group('exp')
        suffix = self.match.group('suffix')
        if int_part:
            result = int(int_part)
        if float_part:
            result += float('0.{}'.format(float_part))
        if exp_part:
            result *= 10 ** float(exp_part)
        if suffix:
            # all suffixes in LITERAL_SUFFIXES are lowercase, but we want to have
            # case-insensitive suffixes: 10mb and 10MB should mean the same thing.
            try:
                result *= LITERAL_SUFFIXES[suffix.lower()]
            except KeyError:
                raise UnknownLiteralSuffixError(suffix, self)
        return result

    def prefix(self, parser):
        return expr.LiteralExpr(self.value)


class StringToken(Token):
    def prefix(self, parser):
        return expr.LiteralExpr(self.match.group('string'))


class NameToken(Token):
    def prefix(self, parser):
        return expr.NameExpr(self.text)


class ConcatToken(OperatorToken):
    operator_name = '||'


class DivToken(OperatorToken):
    operator_name = '/'


class EqToken(OperatorToken):
    operator_name = '='


class GtToken(OperatorToken):
    operator_name = '>'


class GteToken(OperatorToken):
    operator_name = '>='


class LtToken(OperatorToken):
    operator_name = '<'


class LteToken(OperatorToken):
    operator_name = '<='


class MinusToken(OperatorToken):
    operator_name = '-'

    def prefix(self, parser):
        return expr.FunctionExpr('negate', [parser.expr(left_bp=self.left_bp)])


class ModuloToken(OperatorToken):
    operator_name = '%'


class MulToken(OperatorToken):
    operator_name = '*'


class NeToken(OperatorToken):
    operator_name = '<>'


class PlusToken(OperatorToken):
    operator_name = '+'

    def prefix(self, parser):
        return parser.expr(left_bp=self.left_bp)


class PowerToken(OperatorToken):
    operator_name = '^'


class SpecialToken(Token):
    """Base class for special tokens: parens, commas, periods etc."""


class OpeningParenToken(SpecialToken):
    def prefix(self, parser):
        if isinstance(parser.token, ClosingParenToken):
            raise LexerError('expression expected', self.start())
        result = parser.expr()
        if not isinstance(parser.token, ClosingParenToken):
            raise LexerError(') expected', parser.token.start)
        parser.advance()
        return result

    def suffix(self, left, parser):
        if not isinstance(left, expr.NameExpr):
            raise LexerError('expected name, got: {!r}'.format(left), self.start)
        if isinstance(parser.token, ClosingParenToken):
            args = []
        else:
            args = parser.parse_delimited_exprs(CommaToken)
        parser.skip(ClosingParenToken)
        return expr.FunctionExpr(left.name, args)


class ClosingParenToken(SpecialToken):
    pass


class CommaToken(SpecialToken):
    pass


class PeriodToken(SpecialToken):
    pass  # not implemented yet


class EndQueryToken(Token):
    """Sentinel token with zero right binding power. Parsing will not go through it."""


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
        end_re = _regex('$')
        yield EndQueryToken(end_re.match(string, pos=start))

    def tokenize(self, string):
        assert isinstance(string, unicode)
        for token in self.tokenize_with_whitespaces(string):
            if not isinstance(token, WhitespaceToken):
                yield token


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


_OPERATOR_CHARS = set()  # populated in _add_operators


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


def _add_number_literals(lexer):
    # TODO: check that regexes are in sync with NumberToken
    patterns = [
        # [2].3[e[-]5][years]
        r'(?P<int>\d*)\.(?P<float>\d+)(?:e[+-]?(?P<exp>\d+))?(?P<suffix>[^\W\d]+)?\b',
        # 2.[e[-]5][years]
        r'(?P<int>\d+)\.(?P<float>)(?:(?:e[+-]?(?P<exp>\d+))?(?P<suffix>[^\W\d]+)?\b)?',
        # 2[e[-]5][years]
        r'(?P<int>\d+)(?P<float>)(?:e[+-]?(?P<exp>\d+))?(?P<suffix>[^\W\d]+)?\b',
    ]
    for pattern in patterns:
        lexer.add(_regex(pattern, extra_flags=re.IGNORECASE), NumberToken)


def _add_whitespace(lexer):
    lexer.add(_regex(r'\s+'), WhitespaceToken)


def _operator(s):
    chars = ''.join(_OPERATOR_CHARS)
    return _regex(r'{}(?![{}])'.format(re.escape(s), re.escape(chars)))


def _get_left_binding_powers():
    # increasing precedence levels
    left_token_groups = [
        [],  # empty group, so next group will have non-zero precedence level
        [PlusToken, MinusToken],  # unary plus/minus
    ]
    # huge multiplier, because unary plus/minus should have high precedence level
    return _get_binding_powers(left_token_groups, mul=10000)


def _get_right_binding_powers():
    # increasing precedence levels, first level is zero
    right_token_groups = [
        [EndToken, CommaToken, ClosingParenToken, FromToken, WhereToken, OrderToken,
         AscToken, DescToken, LimitToken, OffsetToken, EndQueryToken],

        # TODO(aershov182): make precedence levels like in postgres
        [OrToken],
        [AndToken],
        [EqToken, NeToken],
        [LtToken, LteToken, GtToken, GteToken],
        [LikeToken, IlikeToken, LikeRegexToken, RlikeToken, RilikeToken, ContainsToken, IcontainsToken],
        [BetweenToken],
        [InToken],
        [ConcatToken],
        [PlusToken, MinusToken],
        [MulToken, DivToken, ModuloToken],
        [PowerToken],
        [OpeningParenToken],
    ]
    return _get_binding_powers(right_token_groups)


# multiply by 100 so we can add some inbetweener precedence level
def _get_binding_powers(token_groups, mul=100):
    powers = {}
    for level, group in enumerate(token_groups):
        for op in group:
            assert op not in powers
            powers[op] = mul * level
    return powers


LEFT_BINDING_POWERS = _get_left_binding_powers()
RIGHT_BINDING_POWERS = _get_right_binding_powers()

tokenize = _make_default_lexer().tokenize
