from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from lsql import tokens


def keyword_test_case(keyword, token_class):
    return keyword, token_class(keyword, tokens.Position(keyword, 0, len(keyword)))


@pytest.mark.parametrize('string, token', [
    keyword_test_case('and', tokens.AndToken),
    keyword_test_case('as', tokens.AsToken),
    keyword_test_case('asc', tokens.AscToken),
    keyword_test_case('between', tokens.BetweenToken),
    keyword_test_case('by', tokens.ByToken),
    keyword_test_case('case', tokens.CaseToken),
    keyword_test_case('contains', tokens.ContainsToken),
    keyword_test_case('delete', tokens.DeleteToken),
    keyword_test_case('desc', tokens.DescToken),
    keyword_test_case('drop', tokens.DropToken),
    keyword_test_case('else', tokens.ElseToken),
    keyword_test_case('end', tokens.EndToken),
    keyword_test_case('exists', tokens.ExistsToken),
    keyword_test_case('from', tokens.FromToken),
    keyword_test_case('group', tokens.GroupToken),
    keyword_test_case('having', tokens.HavingToken),
    keyword_test_case('ilike', tokens.IlikeToken),
    keyword_test_case('in', tokens.InToken),
    keyword_test_case('is', tokens.IsToken),
    keyword_test_case('isnull', tokens.IsNullToken),
    keyword_test_case('join', tokens.JoinToken),
    keyword_test_case('left', tokens.LeftToken),
    keyword_test_case('like', tokens.LikeToken),
    keyword_test_case('like_regex', tokens.LikeRegexToken),
    keyword_test_case('limit', tokens.LimitToken),
    keyword_test_case('not', tokens.NotToken),
    keyword_test_case('notnull', tokens.NotNullToken),
    keyword_test_case('null', tokens.NullToken),
    keyword_test_case('offset', tokens.OffsetToken),
    keyword_test_case('or', tokens.OrToken),
    keyword_test_case('order', tokens.OrderToken),
    keyword_test_case('outer', tokens.OuterToken),
    keyword_test_case('select', tokens.SelectToken),
    keyword_test_case('then', tokens.ThenToken),
    keyword_test_case('update', tokens.UpdateToken),
    keyword_test_case('where', tokens.WhereToken),
])
def test_keywords(string, token):
    assert list(tokens.tokenize(string)) == [token]


def test_operators():
    pass


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
