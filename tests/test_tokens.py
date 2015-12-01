from __future__ import absolute_import, division, print_function, unicode_literals

import logging

import pytest

from lsql import tokens

# logging.basicConfig(level=logging.DEBUG)


def make_test_case(string, expected_token_class):
    return string, expected_token_class(string, tokens.Position(string, 0, len(string)))


@pytest.mark.parametrize('string, token', [
    make_test_case('and', tokens.AndToken),
    make_test_case('as', tokens.AsToken),
    make_test_case('asc', tokens.AscToken),
    make_test_case('between', tokens.BetweenToken),
    make_test_case('by', tokens.ByToken),
    make_test_case('case', tokens.CaseToken),
    make_test_case('contains', tokens.ContainsToken),
    make_test_case('delete', tokens.DeleteToken),
    make_test_case('desc', tokens.DescToken),
    make_test_case('drop', tokens.DropToken),
    make_test_case('else', tokens.ElseToken),
    make_test_case('end', tokens.EndToken),
    make_test_case('exists', tokens.ExistsToken),
    make_test_case('from', tokens.FromToken),
    make_test_case('group', tokens.GroupToken),
    make_test_case('having', tokens.HavingToken),
    make_test_case('icontains', tokens.IcontainsToken),
    make_test_case('ilike', tokens.IlikeToken),
    make_test_case('in', tokens.InToken),
    make_test_case('is', tokens.IsToken),
    make_test_case('isnull', tokens.IsNullToken),
    make_test_case('join', tokens.JoinToken),
    make_test_case('left', tokens.LeftToken),
    make_test_case('like', tokens.LikeToken),
    make_test_case('like_regex', tokens.LikeRegexToken),
    make_test_case('limit', tokens.LimitToken),
    make_test_case('not', tokens.NotToken),
    make_test_case('notnull', tokens.NotNullToken),
    make_test_case('null', tokens.NullToken),
    make_test_case('offset', tokens.OffsetToken),
    make_test_case('or', tokens.OrToken),
    make_test_case('order', tokens.OrderToken),
    make_test_case('outer', tokens.OuterToken),
    make_test_case('rilike', tokens.RilikeToken),
    make_test_case('rlike', tokens.RlikeToken),
    make_test_case('select', tokens.SelectToken),
    make_test_case('then', tokens.ThenToken),
    make_test_case('update', tokens.UpdateToken),
    make_test_case('where', tokens.WhereToken),
])
def test_keywords(string, token):
    assert list(tokens.tokenize(string)) == [token]


@pytest.mark.parametrize('string, token', [
    make_test_case('||', tokens.ConcatToken),
    make_test_case('/', tokens.DivToken),
    make_test_case('=', tokens.EqToken),
    make_test_case('>', tokens.GtToken),
    make_test_case('>=', tokens.GteToken),
    make_test_case('<', tokens.LtToken),
    make_test_case('<=', tokens.LteToken),
    make_test_case('-', tokens.MinusToken),
    make_test_case('%', tokens.ModuloToken),
    make_test_case('*', tokens.MulToken),
    make_test_case('<>', tokens.NeToken),
    make_test_case('!=', tokens.NeToken),
    make_test_case('+', tokens.PlusToken),
    make_test_case('^', tokens.PowerToken),
])
def test_operators(string, token):
    assert list(tokens.tokenize(string)) == [token]


@pytest.mark.parametrize('string, token', [
    make_test_case('23', tokens.NumberToken),
    make_test_case('2.3', tokens.NumberToken),
    make_test_case('2.', tokens.NumberToken),
    make_test_case('2e5', tokens.NumberToken),
    make_test_case('2.5e5', tokens.NumberToken),
    make_test_case('2k', tokens.NumberToken),
    make_test_case('2.5year', tokens.NumberToken),
    make_test_case('2.year', tokens.NumberToken),
])
def test_number_literals(string, token):
    assert list(tokens.tokenize(string)) == [token]


@pytest.mark.parametrize('string, token', [
    make_test_case(',', tokens.CommaToken),
    make_test_case(')', tokens.ClosingParenToken),
    make_test_case('(', tokens.OpeningParenToken),
    make_test_case('.', tokens.PeriodToken),
])
def test_special_characters(string, token):
    assert list(tokens.tokenize(string)) == [token]


@pytest.mark.parametrize('string, token', [
    make_test_case("''", tokens.StringToken),
    make_test_case("'test'", tokens.StringToken),
    make_test_case("'te''st'", tokens.StringToken),
])
def test_string_literals(string, token):
    assert list(tokens.tokenize(string)) == [token]


# TODO: check token contents
@pytest.mark.parametrize('string, expected_token_classes', [
    ('-3', [tokens.MinusToken, tokens.NumberToken]),
    ("SELECT length(LINES) AS num_lines "
     "FROM '/tmp' "
     "WHERE ext = 'py' AND size > 3kb OR age(mtime) >= 1.5year "
     "GROUP BY dir "
     "ORDER BY size",
     [tokens.SelectToken, tokens.NameToken, tokens.OpeningParenToken,
      tokens.NameToken, tokens.ClosingParenToken, tokens.AsToken, tokens.NameToken,
      tokens.FromToken, tokens.StringToken,
      tokens.WhereToken, tokens.NameToken, tokens.EqToken, tokens.StringToken,
      tokens.AndToken, tokens.NameToken, tokens.GtToken, tokens.NumberToken,
      tokens.OrToken, tokens.NameToken, tokens.OpeningParenToken, tokens.NameToken,
      tokens.ClosingParenToken, tokens.GteToken, tokens.NumberToken,
      tokens.GroupToken, tokens.ByToken, tokens.NameToken,
      tokens.OrderToken, tokens.ByToken, tokens.NameToken
      ]),
])
def test_full_query(string, expected_token_classes):
    assert_classes_equal(
        list(tokens.tokenize(string)),
        expected_token_classes
    )


@pytest.mark.parametrize('string, expected_token_classes', [
    ('SELECT  path', [tokens.SelectToken, tokens.NameToken]),  # two whitespaces
    ('SELECT\tpath', [tokens.SelectToken, tokens.NameToken]),
    ('SELECT\npath', [tokens.SelectToken, tokens.NameToken]),
])
def test_whitespace(string, expected_token_classes):
    assert_classes_equal(
        list(tokens.tokenize(string)),
        expected_token_classes
    )


def assert_classes_equal(objects, expected_classes):
    classes = [obj.__class__ for obj in objects]
    assert classes == expected_classes


# TODO: test bad operators (`<=>`) etc
def test_bad_queries():
    pass
