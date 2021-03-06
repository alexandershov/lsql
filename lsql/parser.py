from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial, wraps
import logging
import re

from lsql import ast
from lsql.errors import LsqlError

logger = logging.getLogger(__name__)

# TODO(aershov182): implement all essential not implemented tokens: NotToken, GroupToken etc.

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
    pass


class CantTokenizeError(LexerError):
    def __init__(self, string, pos):
        self.string = string
        self.pos = pos

    def __str__(self):
        substring = self.string[self.pos:self.pos + 20] + '...'
        return "Can't tokenize at position {:d}: {!r}".format(self.pos, substring)


class NotImplementedTokenError(LexerError):
    def __init__(self, token_class, match):
        self.token_class = token_class
        self.match = match


class ParserError(LsqlError):
    pass


class UnexpectedTokenError(ParserError):
    def __init__(self, expected_token_class, actual_token):
        self.expected_token_class = expected_token_class
        self.actual_token = actual_token


class UnexpectedEndError(ParserError):
    pass


class UnknownLiteralSuffixError(ParserError):
    def __init__(self, suffix, token):
        self.suffix = suffix
        self.token = token

    @property
    def known_suffixes(self):
        return LITERAL_SUFFIXES.keys()


class OperatorExpectedError(ParserError):
    def __init__(self, token):
        self.token = token


class ValueExpectedError(ParserError):
    def __init__(self, token):
        self.token = token


def location_from_match(match):
    return ast.Location(text=match.group(), start=match.start(), end=match.end())


def location_from_tokens(*tokens):
    assert tokens
    start = tokens[0].start
    end = tokens[-1].end
    text = tokens[0].text[start:end]
    return ast.Location(text=text, start=start, end=end)


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
            raise UnexpectedEndError('unexpected end of query')

    def peek(self):
        self._check_bounds(self._index + 1)
        return self._tokens[self._index + 1]

    @property
    def token(self):
        return self._tokens[self._index]

    def parse(self):
        # order of _get_clause calls is important, because order of clauses is important in SQL
        select_node = self._get_clause(SelectToken)
        from_node = self._get_clause(FromToken)
        where_node = self._get_clause(WhereToken)
        group_node = self._get_clause(GroupToken)
        having_node = self._get_clause(HavingToken)
        order_node = self._get_clause(OrderToken)
        limit_node = self._get_clause(LimitToken)
        offset_node = self._get_clause(OffsetToken)

        self.expect(EndQueryToken)

        return ast.QueryNode.create(
            select_node=select_node,
            from_node=from_node,
            where_node=where_node,
            group_node=group_node,
            having_node=having_node,
            order_node=order_node,
            limit_node=limit_node,
            offset_node=offset_node,
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
        nodes = [parse_fn()]
        while isinstance(self.token, delimiter_token_cls):
            self.advance()
            nodes.append(parse_fn())
        return nodes


def parse(tokens):
    return Parser(tokens).parse()


def not_implemented(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    wrapper.not_implemented = True
    return wrapper


# TODO(aershov182): add methods that'll help to figure out that these token has redefined
# TODO(aershov182): ... .suffix(), .prefix(), and .clause() methods.
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
            if not self.implemented_suffix():
                raise OperatorExpectedError(self)
            raise NotImplementedError('please add {} to RIGHT_BINDING_POWERS'.format(cls.__name__))

    @not_implemented
    def prefix(self, parser):
        """
        Called when token is encountered in prefix position.
        :type parser: lsql.parser.Parser
        :rtype: lsql.ast.Node

        Examples (^ means current token position):

        * In this case we call MinusToken().prefix(parser):
          -3
          ^

        * In this case we call NumberToken(4).prefix(parser):
          2 - 4
              ^
        """
        raise ValueExpectedError(self)

    @not_implemented
    def suffix(self, left, parser):
        """
        Called when token is encountered in suffix position.

        :param left: Node to the left of the token.
        :type left: lsql.ast.Node
        :type parser: lsql.parser.Parser
        :rtype: lsql.ast.Node

        Example (^ means current token position):

        * In this case we call MinusToken().suffix(Literalnode(2), parser):
          2 - 4
            ^
        """
        raise NotImplementedError(self._get_not_implemented_message('suffix'))

    @not_implemented
    def clause(self, parser):
        """
        Called in special cases. For example Parser.parse() will call .clause() on
        SelectToken, FromToken, WhereToken etc.

        :type parser: lsql.parser.Parser
        :rtype: lsql.ast.Node
        """
        raise NotImplementedError(self._get_not_implemented_message('clause'))

    def _get_not_implemented_message(self, method):
        return 'not implemented method .{!s}() in {!r}'.format(method, self)

    # TODO: think of something better than implemented_* methods that use getattr

    @classmethod
    def implemented_prefix(cls):
        return not getattr(cls.prefix, 'not_implemented', False)

    @classmethod
    def implemented_suffix(cls):
        return not getattr(cls.suffix, 'not_implemented', False)

    @classmethod
    def implemented_clause(cls):
        return not getattr(cls.clause, 'not_implemented', False)

    @classmethod
    def get_human_name(cls):
        return cls.__name__

    def __repr__(self):
        return '{:s}(text={!r}, start={!r}, end={!r})'.format(
            self.__class__.__name__, self.text, self.start, self.end
        )


class NotImplementedToken(Token):
    def __init__(self, match):
        # TODO: maybe we can reuse Token class here?
        raise NotImplementedTokenError(token_class=self.__class__, match=match)


class KeywordToken(Token):
    """Base class for keyword tokens."""
    keyword = None  # redefine me in subclasses

    @classmethod
    def get_human_name(cls):
        return cls.keyword


class AsToken(NotImplementedToken, KeywordToken):
    keyword = 'as'


class AscToken(KeywordToken):
    direction = ast.ASC
    keyword = 'asc'


class DescToken(KeywordToken):
    direction = ast.DESC
    keyword = 'desc'


class BetweenToken(KeywordToken):
    keyword = 'between'

    def suffix(self, left, parser):
        first = parser.expr(left_bp=self.right_bp)
        parser.skip(AndToken)
        last = parser.expr()
        return ast.BetweenNode.create(left, first, last)


class CaseToken(NotImplementedToken, KeywordToken):
    keyword = 'case'


class ByToken(KeywordToken):
    keyword = 'by'


class ContainsToken(NotImplementedToken, KeywordToken):
    keyword = 'contains'


class CountToken(KeywordToken):
    keyword = 'count'

    def prefix(self, parser):
        parser.skip(OpeningParenToken)
        if isinstance(parser.token, MulToken):
            parser.advance()
            arg_node = ast.ValueNode.create(1)
        else:
            arg_node = parser.expr()
        parser.skip(ClosingParenToken)
        return ast.FunctionNode.create('count', arg_nodes=[arg_node])


class DeleteToken(NotImplementedToken, KeywordToken):
    keyword = 'delete'


class DropToken(NotImplementedToken, KeywordToken):
    keyword = 'drop'


class ElseToken(NotImplementedToken, KeywordToken):
    keyword = 'else'


class EndToken(NotImplementedToken, KeywordToken):
    keyword = 'end'


class ExistsToken(NotImplementedToken, KeywordToken):
    keyword = 'exists'


class FromToken(KeywordToken):
    keyword = 'from'

    def clause(self, parser):
        return parser.expr()


class GroupToken(KeywordToken):
    keyword = 'group'

    def clause(self, parser):
        parser.skip(ByToken)
        return ast.GroupNode.create(parser.parse_delimited_exprs(CommaToken))


class HavingToken(KeywordToken):
    keyword = 'having'

    def clause(self, parser):
        return parser.expr()


class IsToken(NotImplementedToken, KeywordToken):
    keyword = 'is'


class IsNullToken(NotImplementedToken, KeywordToken):
    keyword = 'isnull'


class JoinToken(NotImplementedToken, KeywordToken):
    keyword = 'join'


class LeftToken(NotImplementedToken, KeywordToken):
    keyword = 'left'


class AndToken(KeywordToken):
    keyword = 'and'

    def suffix(self, left, parser):
        return ast.AndNode.create(left, parser.expr(self.right_bp))


class OrToken(KeywordToken):
    keyword = 'or'

    def suffix(self, left, parser):
        return ast.OrNode.create(left, parser.expr(self.right_bp))


class OperatorToken(Token):
    operator_name = None  # should be redefined in subclasses

    def suffix(self, left, parser):
        right = parser.expr(self.right_bp)
        return ast.FunctionNode.create(self.operator_name, [left, right])


class InToken(OperatorToken, KeywordToken):
    keyword = 'in'
    operator_name = 'in'

    def suffix(self, left, parser):
        parser.skip(OpeningParenToken)
        nodes = parser.parse_delimited_exprs(CommaToken)
        parser.skip(ClosingParenToken)
        return ast.FunctionNode.create(self.operator_name, [left, ast.ArrayNode.create(nodes)])


class LikeToken(NotImplementedToken, OperatorToken, KeywordToken):
    keyword = 'like'


# alias for rlike
class LikeRegexToken(NotImplementedToken, OperatorToken, KeywordToken):
    keyword = 'like_regex'


class IcontainsToken(NotImplementedToken, OperatorToken, KeywordToken):
    keyword = 'icontains'


class IlikeToken(NotImplementedToken, OperatorToken, KeywordToken):
    keyword = 'ilike'


class LimitToken(KeywordToken):
    keyword = 'limit'

    def clause(self, parser):
        return parser.expr()


class NotToken(NotImplementedToken, OperatorToken, KeywordToken):
    keyword = 'not'


class NotNullToken(NotImplementedToken, KeywordToken):
    keyword = 'notnull'


class NullToken(KeywordToken):
    keyword = 'null'

    def prefix(self, parser):
        return ast.ValueNode.create(ast.NULL)


class OffsetToken(KeywordToken):
    keyword = 'offset'

    def clause(self, parser):
        return parser.expr()


class OrderToken(KeywordToken):
    keyword = 'order'

    def clause(self, parser):
        parser.skip(ByToken)
        sub_nodes = parser.parse_delimited_exprs(
            CommaToken,
            parse_fn=partial(_parse_one_order_by_clause, parser=parser)
        )
        return ast.OrderNode.create(sub_nodes)


def _parse_one_order_by_clause(parser):
    part_node = parser.expr()
    if isinstance(parser.token, (AscToken, DescToken)):
        direction = parser.token.direction
        parser.advance()
    else:
        direction = ast.ASC
    return ast.OrderByPartNode.create(part_node, direction)


class OuterToken(NotImplementedToken, KeywordToken):
    keyword = 'outer'


# TODO: maybe should be OperatorToken?
class RlikeToken(NotImplementedToken, KeywordToken):
    keyword = 'rlike'


class RilikeToken(NotImplementedToken, KeywordToken):
    keyword = 'rilike'


class SelectToken(KeywordToken):
    keyword = 'select'

    def clause(self, parser):
        if isinstance(parser.token, MulToken):
            select_node = ast.SelectStarNode.create()
            parser.advance()
        else:
            select_node = ast.SelectNode.create(children=parser.parse_delimited_exprs(CommaToken))
        return select_node


class ThenToken(NotImplementedToken, KeywordToken):
    keyword = 'then'


class UpdateToken(NotImplementedToken, KeywordToken):
    keyword = 'update'


class WhereToken(KeywordToken):
    keyword = 'where'

    def clause(self, parser):
        return parser.expr()


class WhitespaceToken(Token):
    pass


class NumberToken(Token):
    def prefix(self, parser):
        return ast.ValueNode.create(self.value)

    @property
    def value(self):
        result = 0
        # self.match is a match of some regex from _add_number_literals
        int_part = self.match.group('int')
        float_part = self.match.group('float')
        exp_part = self.match.group('exp')
        suffix_part = self.match.group('suffix')
        if int_part:
            result = int(int_part)
        if float_part:
            result += float('0.{}'.format(float_part))
        if exp_part:
            result *= 10 ** float(exp_part)
        if suffix_part:
            try:
                # all suffixes in LITERAL_SUFFIXES are lowercase, but we want to have
                # case-insensitive suffixes: 10mb and 10MB should mean the same thing.
                result *= LITERAL_SUFFIXES[suffix_part.lower()]
            except KeyError:
                raise UnknownLiteralSuffixError(suffix_part, self)
        return result


class StringToken(Token):
    def prefix(self, parser):
        return ast.ValueNode.create(self.match.group('string'))


class NameToken(Token):
    def prefix(self, parser):
        return ast.NameNode.create(self.text)


class EqToken(OperatorToken):
    operator_name = '='


class NeToken(OperatorToken):
    operator_name = '<>'


class LtToken(OperatorToken):
    operator_name = '<'


class LteToken(OperatorToken):
    operator_name = '<='


class GtToken(OperatorToken):
    operator_name = '>'


class GteToken(OperatorToken):
    operator_name = '>='


class ConcatToken(OperatorToken):
    operator_name = '||'


class MinusToken(OperatorToken):
    operator_name = '-'

    # handles unary minus
    def prefix(self, parser):
        return ast.FunctionNode.create('negate', [parser.expr(left_bp=self.left_bp)])


class PlusToken(OperatorToken):
    operator_name = '+'

    # handles unary plus
    def prefix(self, parser):
        return parser.expr(left_bp=self.left_bp)


class MulToken(OperatorToken):
    operator_name = '*'


class DivToken(OperatorToken):
    operator_name = '/'


class ModuloToken(OperatorToken):
    operator_name = '%'


class PowerToken(OperatorToken):
    operator_name = '^'


class SpecialToken(Token):
    """Base class for special tokens: parens, commas, periods etc."""
    string = None  # redefine me in subclasses

    @classmethod
    def get_human_name(cls):
        return cls.string


class OpeningParenToken(SpecialToken):
    string = '('

    def prefix(self, parser):
        if isinstance(parser.token, ClosingParenToken):
            raise UnexpectedTokenError(None, parser.token)
        result_node = parser.expr()
        parser.skip(ClosingParenToken)
        return result_node

    def suffix(self, left, parser):
        # TODO(aershov182): raise some appropriate exception when Node class will have it's full
        # TODO(aershov182): ... position in string
        assert isinstance(left, ast.NameNode)
        if isinstance(parser.token, ClosingParenToken):
            args = []
        else:
            args = parser.parse_delimited_exprs(CommaToken)
        parser.skip(ClosingParenToken)
        return ast.FunctionNode.create(left.name, args)


class ClosingParenToken(SpecialToken):
    string = ')'


class CommaToken(SpecialToken):
    string = ','


class PeriodToken(NotImplementedToken, SpecialToken):
    string = '.'


class EndQueryToken(Token):
    """Sentinel token with right binding power equal to zero. Parsing will not go through it."""
    @classmethod
    def get_human_name(cls):
        # TODO: check that string is ok in all cases
        return '<END OF QUERY>'


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
                raise CantTokenizeError(string, start)
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
    # special should go after number_literals because of '.2' which is a NumberToken.
    # and we don't want it to be a PeriodToken followed by NumberToken
    _add_special(lexer)
    return lexer


def _add_special(lexer):
    special_token_classes = [
        ClosingParenToken,
        CommaToken,
        OpeningParenToken,
        PeriodToken,
    ]
    for special_class in special_token_classes:
        pattern = r'\{}'.format(special_class.string)
        lexer.add(_regex(pattern), special_class)


def _add_keywords(lexer):
    keyword_token_classes = [
        AndToken,
        AsToken,
        AscToken,
        BetweenToken,
        ByToken,
        CaseToken,
        ContainsToken,
        DeleteToken,
        DescToken,
        DropToken,
        CountToken,
        ElseToken,
        EndToken,
        ExistsToken,
        FromToken,
        GroupToken,
        HavingToken,
        IcontainsToken,
        IlikeToken,
        InToken,
        IsToken,
        IsNullToken,
        JoinToken,
        LeftToken,
        LikeToken,
        LikeRegexToken,
        LimitToken,
        NotToken,
        NotNullToken,
        NullToken,
        OffsetToken,
        OrToken,
        OrderToken,
        OuterToken,
        RilikeToken,
        RlikeToken,
        SelectToken,
        ThenToken,
        UpdateToken,
        WhereToken,
    ]
    for keyword_class in keyword_token_classes:
        lexer.add(_keyword(keyword_class.keyword), keyword_class)


def _add_names(lexer):
    lexer.add(_regex(r'[^\W\d]\w*'), NameToken)


_OPERATOR_CHARS = set()  # populated in _add_operators


def _add_operators(lexer):
    patterns_with_operator_classes = [
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
    for pattern, _ in patterns_with_operator_classes:
        _OPERATOR_CHARS.update(pattern)
    for pattern, operator_class in patterns_with_operator_classes:
        lexer.add(_operator(pattern), operator_class)


def _add_string_literals(lexer):
    lexer.add(_regex(r"'(?P<string>(?:[^']|'')*)'"), StringToken)


def _add_number_literals(lexer):
    # TODO: check that regexes are in sync with NumberToken
    number_patterns = [
        # [2].3[e[+-]5][years]
        r'(?P<int>\d*)\.(?P<float>\d+)(?:e(?P<exp>[+-]?\d+))?(?P<suffix>[^\W\d]+)?\b',
        # 2.[e[+-]5][years]
        r'(?P<int>\d+)\.(?P<float>)(?:(?:e(?P<exp>[+-]?\d+))?(?P<suffix>[^\W\d]+)?\b)?',
        # 2[e[+-]5][years]
        r'(?P<int>\d+)(?P<float>)(?:e(?P<exp>[+-]?\d+))?(?P<suffix>[^\W\d]+)?\b',
    ]
    for pattern in number_patterns:
        lexer.add(_regex(pattern, extra_flags=re.IGNORECASE), NumberToken)


def _add_whitespace(lexer):
    lexer.add(_regex(r'\s+'), WhitespaceToken)


def _operator(s):
    chars = ''.join(_OPERATOR_CHARS)
    return _regex(r'{}(?![{}])'.format(re.escape(s), re.escape(chars)))


def _get_right_binding_powers():
    # increasing precedence levels, first level is zero
    right_token_groups = [
        [EndToken, CommaToken, ClosingParenToken, FromToken, WhereToken, GroupToken, HavingToken, OrderToken,
         AscToken, DescToken, LimitToken, OffsetToken, EndQueryToken],

        [OrToken],
        [AndToken],
        [EqToken],
        [LtToken, GtToken],
        [LikeToken, IlikeToken, LikeRegexToken, RlikeToken, RilikeToken, ContainsToken, IcontainsToken],
        [BetweenToken],
        [InToken],
        [ConcatToken, LteToken, GteToken, NeToken],
        [PlusToken, MinusToken],
        [MulToken, DivToken, ModuloToken],
        [PowerToken],
        [OpeningParenToken],
    ]
    return _get_binding_powers(right_token_groups)


# multiply by 100 so we can add some in-between precedence levels
def _get_binding_powers(token_groups, mul=100):
    powers = {}
    for level, group in enumerate(token_groups):
        for operator_class in group:
            assert operator_class not in powers
            powers[operator_class] = mul * level
    return powers


# we need to define binding powers at the end of the file, because we need tokens to be
# defined

LEFT_BINDING_POWERS = {
    # unary plus/minus should have max binding power, so '-3 + 2' is parsed as '(-3) + 2'
    # not '-(3 + 2)'
    PlusToken: float('inf'),
    MinusToken: float('inf'),
}
RIGHT_BINDING_POWERS = _get_right_binding_powers()

tokenize = _make_default_lexer().tokenize
