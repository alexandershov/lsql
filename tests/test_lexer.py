from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
import pytest

from lsql import lexer


class Match(namedtuple('TestMatch', ['string', 'pos', 'endpos'])):
    def start(self):
        return self.pos

    def end(self):
        return self.endpos

    def group(self):
        return self.string[self.pos:self.endpos]


def make_test_case(string, expected_token_class):
    return string, expected_token_class(Match(string, 0, len(string)))


@pytest.mark.parametrize('string, token', [
    make_test_case('and', lexer.AndToken),
    make_test_case('as', lexer.AsToken),
    make_test_case('asc', lexer.AscToken),
    make_test_case('between', lexer.BetweenToken),
    make_test_case('by', lexer.ByToken),
    make_test_case('case', lexer.CaseToken),
    make_test_case('contains', lexer.ContainsToken),
    make_test_case('delete', lexer.DeleteToken),
    make_test_case('desc', lexer.DescToken),
    make_test_case('drop', lexer.DropToken),
    make_test_case('else', lexer.ElseToken),
    make_test_case('end', lexer.EndToken),
    make_test_case('exists', lexer.ExistsToken),
    make_test_case('from', lexer.FromToken),
    make_test_case('group', lexer.GroupToken),
    make_test_case('having', lexer.HavingToken),
    make_test_case('icontains', lexer.IcontainsToken),
    make_test_case('ilike', lexer.IlikeToken),
    make_test_case('in', lexer.InToken),
    make_test_case('is', lexer.IsToken),
    make_test_case('isnull', lexer.IsNullToken),
    make_test_case('join', lexer.JoinToken),
    make_test_case('left', lexer.LeftToken),
    make_test_case('like', lexer.LikeToken),
    make_test_case('like_regex', lexer.LikeRegexToken),
    make_test_case('limit', lexer.LimitToken),
    make_test_case('not', lexer.NotToken),
    make_test_case('notnull', lexer.NotNullToken),
    make_test_case('null', lexer.NullToken),
    make_test_case('offset', lexer.OffsetToken),
    make_test_case('or', lexer.OrToken),
    make_test_case('order', lexer.OrderToken),
    make_test_case('outer', lexer.OuterToken),
    make_test_case('rilike', lexer.RilikeToken),
    make_test_case('rlike', lexer.RlikeToken),
    make_test_case('select', lexer.SelectToken),
    make_test_case('then', lexer.ThenToken),
    make_test_case('update', lexer.UpdateToken),
    make_test_case('where', lexer.WhereToken),
])
def test_keywords(string, token):
    assert_tokenizes_to(string, [token])


@pytest.mark.parametrize('string, token', [
    make_test_case('path', lexer.NameToken),
    make_test_case('_path', lexer.NameToken),
    make_test_case('path2', lexer.NameToken),
])
def test_names(string, token):
    assert_tokenizes_to(string, [token])


@pytest.mark.parametrize('string, token', [
    make_test_case('||', lexer.ConcatToken),
    make_test_case('/', lexer.DivToken),
    make_test_case('=', lexer.EqToken),
    make_test_case('>', lexer.GtToken),
    make_test_case('>=', lexer.GteToken),
    make_test_case('<', lexer.LtToken),
    make_test_case('<=', lexer.LteToken),
    make_test_case('-', lexer.MinusToken),
    make_test_case('%', lexer.ModuloToken),
    make_test_case('*', lexer.MulToken),
    make_test_case('<>', lexer.NeToken),
    make_test_case('!=', lexer.NeToken),
    make_test_case('+', lexer.PlusToken),
    make_test_case('^', lexer.PowerToken),
])
def test_operators(string, token):
    assert_tokenizes_to(string, [token])


@pytest.mark.parametrize('string, token', [
    make_test_case('23', lexer.NumberToken),
    make_test_case('23days', lexer.NumberToken),
    make_test_case('23e52', lexer.NumberToken),
    make_test_case('23e-52', lexer.NumberToken),
    make_test_case('23e52days', lexer.NumberToken),
    make_test_case('23e-52days', lexer.NumberToken),
    make_test_case('.23', lexer.NumberToken),
    make_test_case('.23days', lexer.NumberToken),
    make_test_case('.23e52', lexer.NumberToken),
    make_test_case('.23e-52', lexer.NumberToken),
    make_test_case('.23e52days', lexer.NumberToken),
    make_test_case('.23e-52days', lexer.NumberToken),
    make_test_case('23.', lexer.NumberToken),
    make_test_case('23.days', lexer.NumberToken),
    make_test_case('23.e52', lexer.NumberToken),
    make_test_case('23.e-52', lexer.NumberToken),
    make_test_case('23.e52days', lexer.NumberToken),
    make_test_case('23.e-52days', lexer.NumberToken),
    make_test_case('23.52', lexer.NumberToken),
    make_test_case('23.52days', lexer.NumberToken),
    make_test_case('23.52e52', lexer.NumberToken),
    make_test_case('23.52e-52', lexer.NumberToken),
    make_test_case('23.52e52days', lexer.NumberToken),
    make_test_case('23.52e-52days', lexer.NumberToken),
])
def test_number_literals(string, token):
    assert_tokenizes_to(string, [token])


@pytest.mark.parametrize('string, token', [
    make_test_case(',', lexer.CommaToken),
    make_test_case(')', lexer.ClosingParenToken),
    make_test_case('(', lexer.OpeningParenToken),
    make_test_case('.', lexer.PeriodToken),
])
def test_special_characters(string, token):
    assert_tokenizes_to(string, [token])


@pytest.mark.parametrize('string, token', [
    make_test_case("''", lexer.StringToken),
    make_test_case("'test'", lexer.StringToken),
    make_test_case("'te''st'", lexer.StringToken),
])
def test_string_literals(string, token):
    assert_tokenizes_to(string, [token])


# TODO: check token contents
@pytest.mark.parametrize('string, expected_token_classes', [
    ('-3', [lexer.MinusToken, lexer.NumberToken]),
    ('+3', [lexer.PlusToken, lexer.NumberToken]),
    ("SELECT length(LINES) AS num_lines "
     "FROM '/tmp' "
     "WHERE ext = 'py' AND size > 3kb OR age(mtime) >= 1.5year "
     "GROUP BY dir "
     "ORDER BY size",
     [lexer.SelectToken, lexer.NameToken, lexer.OpeningParenToken,
      lexer.NameToken, lexer.ClosingParenToken, lexer.AsToken, lexer.NameToken,
      lexer.FromToken, lexer.StringToken,
      lexer.WhereToken, lexer.NameToken, lexer.EqToken, lexer.StringToken,
      lexer.AndToken, lexer.NameToken, lexer.GtToken, lexer.NumberToken,
      lexer.OrToken, lexer.NameToken, lexer.OpeningParenToken, lexer.NameToken,
      lexer.ClosingParenToken, lexer.GteToken, lexer.NumberToken,
      lexer.GroupToken, lexer.ByToken, lexer.NameToken,
      lexer.OrderToken, lexer.ByToken, lexer.NameToken
      ]),
])
def test_full_query(string, expected_token_classes):
    assert_classes_equal(
        list(lexer.tokenize(string)),
        expected_token_classes
    )


@pytest.mark.parametrize('string, expected_token_classes', [
    ('SELECT  path', [lexer.SelectToken, lexer.NameToken]),  # two whitespaces
    ('SELECT\tpath', [lexer.SelectToken, lexer.NameToken]),
    ('SELECT\npath', [lexer.SelectToken, lexer.NameToken]),
])
def test_whitespace(string, expected_token_classes):
    assert_classes_equal(
        list(lexer.tokenize(string)),
        expected_token_classes
    )


def assert_classes_equal(objects, expected_classes):
    classes = [obj.__class__ for obj in objects]
    assert classes == expected_classes


# TODO: more test cases
@pytest.mark.parametrize('string', [
    'SELECT <=>',  # unknown operator
    "SELECT 'x",  # unclosed single quote
    "SELECT 'x''",  # unclosed single quote ('' is not a string end)
    '2path2',  # bad literal
    # TODO: what about '23.52.e52' should it raise an Error
])
def test_bad_queries(string):
    with pytest.raises(lexer.LexerError):
        list(lexer.tokenize(string))


def assert_tokenizes_to(string, expected_tokens):
    actual_tokens = list(lexer.tokenize(string))
    assert len(actual_tokens) == len(expected_tokens)
    for actual, expected in zip(actual_tokens, expected_tokens):
        assert same_tokens(actual, expected)


def same_tokens(x, y):
    return (x.__class__, x.text, x.start, x.end) == (y.__class__, y.text, y.start, y.end)
