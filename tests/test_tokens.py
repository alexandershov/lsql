from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from lsql import tokens


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
    make_test_case('/', tokens.DivToken),
    make_test_case('-', tokens.MinusToken),
    make_test_case('*', tokens.MulToken),
    make_test_case('+', tokens.PlusToken),
])
def test_operators(string, token):
    assert list(tokens.tokenize(string)) == [token]


def test_number_literals():
    pass


def test_funcall():
    pass


def test_special_characters():
    pass


def test_string_literals():
    pass


def test_full_query():
    pass
