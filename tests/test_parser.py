from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple

import pytest

from lsql import parser


class Match(namedtuple('Match', ['string', 'start_', 'end_'])):
    def start(self):
        return self.start_

    def end(self):
        return self.end_

    def group(self):
        return self.string[self.start_:self.end_]


def make_test_case(string, expected_token_class):
    expected_tokens = [
        expected_token_class(Match(string=string, start_=0, end_=len(string))),
        parser.EndQueryToken(Match(string=string, start_=len(string), end_=len(string))),
    ]
    return string, expected_tokens


def add_end_query_token(token_classes):
    wrapped = list(token_classes)
    wrapped.append(parser.EndQueryToken)
    return wrapped


@pytest.mark.parametrize('string, tokens', [
    make_test_case('and', parser.AndToken),
    make_test_case('as', parser.AsToken),
    make_test_case('asc', parser.AscToken),
    make_test_case('between', parser.BetweenToken),
    make_test_case('by', parser.ByToken),
    make_test_case('case', parser.CaseToken),
    make_test_case('contains', parser.ContainsToken),
    make_test_case('delete', parser.DeleteToken),
    make_test_case('desc', parser.DescToken),
    make_test_case('drop', parser.DropToken),
    make_test_case('else', parser.ElseToken),
    make_test_case('end', parser.EndToken),
    make_test_case('exists', parser.ExistsToken),
    make_test_case('from', parser.FromToken),
    make_test_case('group', parser.GroupToken),
    make_test_case('having', parser.HavingToken),
    make_test_case('icontains', parser.IcontainsToken),
    make_test_case('ilike', parser.IlikeToken),
    make_test_case('in', parser.InToken),
    make_test_case('is', parser.IsToken),
    make_test_case('isnull', parser.IsNullToken),
    make_test_case('join', parser.JoinToken),
    make_test_case('left', parser.LeftToken),
    make_test_case('like', parser.LikeToken),
    make_test_case('like_regex', parser.LikeRegexToken),
    make_test_case('limit', parser.LimitToken),
    make_test_case('not', parser.NotToken),
    make_test_case('notnull', parser.NotNullToken),
    make_test_case('null', parser.NullToken),
    make_test_case('offset', parser.OffsetToken),
    make_test_case('or', parser.OrToken),
    make_test_case('order', parser.OrderToken),
    make_test_case('outer', parser.OuterToken),
    make_test_case('rilike', parser.RilikeToken),
    make_test_case('rlike', parser.RlikeToken),
    make_test_case('select', parser.SelectToken),
    make_test_case('then', parser.ThenToken),
    make_test_case('update', parser.UpdateToken),
    make_test_case('where', parser.WhereToken),
])
def test_keywords(string, tokens):
    assert_tokenizes_to(string, tokens)


@pytest.mark.parametrize('string, tokens', [
    make_test_case('path', parser.NameToken),
    make_test_case('_path', parser.NameToken),
    make_test_case('path2', parser.NameToken),
])
def test_names(string, tokens):
    assert_tokenizes_to(string, tokens)


@pytest.mark.parametrize('string, tokens', [
    make_test_case('||', parser.ConcatToken),
    make_test_case('/', parser.DivToken),
    make_test_case('=', parser.EqToken),
    make_test_case('>', parser.GtToken),
    make_test_case('>=', parser.GteToken),
    make_test_case('<', parser.LtToken),
    make_test_case('<=', parser.LteToken),
    make_test_case('-', parser.MinusToken),
    make_test_case('%', parser.ModuloToken),
    make_test_case('*', parser.MulToken),
    make_test_case('<>', parser.NeToken),
    make_test_case('!=', parser.NeToken),
    make_test_case('+', parser.PlusToken),
    make_test_case('^', parser.PowerToken),
])
def test_operators(string, tokens):
    assert_tokenizes_to(string, tokens)


@pytest.mark.parametrize('string, tokens', [
    make_test_case('23', parser.NumberToken),
    make_test_case('23days', parser.NumberToken),
    make_test_case('23e52', parser.NumberToken),
    make_test_case('23e-52', parser.NumberToken),
    make_test_case('23e+52', parser.NumberToken),
    make_test_case('23e52days', parser.NumberToken),
    make_test_case('23e-52days', parser.NumberToken),
    make_test_case('.23', parser.NumberToken),
    make_test_case('.23days', parser.NumberToken),
    make_test_case('.23e52', parser.NumberToken),
    make_test_case('.23e-52', parser.NumberToken),
    make_test_case('.23e+52', parser.NumberToken),
    make_test_case('.23e52days', parser.NumberToken),
    make_test_case('.23e-52days', parser.NumberToken),
    make_test_case('23.', parser.NumberToken),
    make_test_case('23.days', parser.NumberToken),
    make_test_case('23.e52', parser.NumberToken),
    make_test_case('23.e-52', parser.NumberToken),
    make_test_case('23.e+52', parser.NumberToken),
    make_test_case('23.e52days', parser.NumberToken),
    make_test_case('23.e-52days', parser.NumberToken),
    make_test_case('23.e+52days', parser.NumberToken),
    make_test_case('23.52', parser.NumberToken),
    make_test_case('23.52days', parser.NumberToken),
    make_test_case('23.52e52', parser.NumberToken),
    make_test_case('23.52e-52', parser.NumberToken),
    make_test_case('23.52e+52', parser.NumberToken),
    make_test_case('23.52e52days', parser.NumberToken),
    make_test_case('23.52e-52days', parser.NumberToken),
    make_test_case('23.52e-52days', parser.NumberToken),
    make_test_case('23.52e+52days', parser.NumberToken),
    # checking that mixing upper/lower case is ok
    make_test_case('23.52E-52dAys', parser.NumberToken),
])
def test_number_literals(string, tokens):
    assert_tokenizes_to(string, tokens)


@pytest.mark.parametrize('string, tokens', [
    make_test_case(',', parser.CommaToken),
    make_test_case(')', parser.ClosingParenToken),
    make_test_case('(', parser.OpeningParenToken),
    make_test_case('.', parser.PeriodToken),
])
def test_special_characters(string, tokens):
    assert_tokenizes_to(string, tokens)


@pytest.mark.parametrize('string, tokens', [
    make_test_case("''", parser.StringToken),
    make_test_case("'test'", parser.StringToken),
    make_test_case("'te''st'", parser.StringToken),
])
def test_string_literals(string, tokens):
    assert_tokenizes_to(string, tokens)


# TODO: check token contents
@pytest.mark.parametrize('string, expected_token_classes', [
    ('-3', add_end_query_token([parser.MinusToken, parser.NumberToken])),
    ('+3', add_end_query_token([parser.PlusToken, parser.NumberToken])),
    ("SELECT length(LINES) AS num_lines "
     "FROM '/tmp' "
     "WHERE ext = 'py' AND size > 3kb OR age(mtime) >= 1.5year "
     "GROUP BY dir "
     "ORDER BY size",
     add_end_query_token([parser.SelectToken, parser.NameToken, parser.OpeningParenToken,
                          parser.NameToken, parser.ClosingParenToken, parser.AsToken,
                          parser.NameToken,
                          parser.FromToken, parser.StringToken,
                          parser.WhereToken, parser.NameToken, parser.EqToken, parser.StringToken,
                          parser.AndToken, parser.NameToken, parser.GtToken, parser.NumberToken,
                          parser.OrToken, parser.NameToken, parser.OpeningParenToken,
                          parser.NameToken,
                          parser.ClosingParenToken, parser.GteToken, parser.NumberToken,
                          parser.GroupToken, parser.ByToken, parser.NameToken,
                          parser.OrderToken, parser.ByToken, parser.NameToken
                          ])),
])
def test_full_query(string, expected_token_classes):
    assert_classes_equal(
        list(parser.tokenize(string)),
        expected_token_classes
    )


@pytest.mark.parametrize('string, expected_token_classes', [
    # two whitespaces
    ('SELECT  path', add_end_query_token([parser.SelectToken, parser.NameToken])),
    ('SELECT\tpath', add_end_query_token([parser.SelectToken, parser.NameToken])),
    ('SELECT\npath', add_end_query_token([parser.SelectToken, parser.NameToken])),
])
def test_whitespace(string, expected_token_classes):
    assert_classes_equal(
        list(parser.tokenize(string)),
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
    with pytest.raises(parser.CantTokenizeError):
        list(parser.tokenize(string))


def assert_tokenizes_to(string, expected_tokens):
    actual_tokens = list(parser.tokenize(string))
    assert len(actual_tokens) == len(expected_tokens)
    for actual, expected in zip(actual_tokens, expected_tokens):
        assert same_tokens(actual, expected)


def same_tokens(x, y):
    return (x.__class__, x.text, x.start, x.end) == (y.__class__, y.text, y.start, y.end)
