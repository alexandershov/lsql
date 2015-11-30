from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from lsql.tokens import (
    AsToken, AscToken, OperatorToken, Position, SelectToken, tokenize,
)



def keyword_test_case(keyword, token_class):
    return keyword, token_class(keyword, Position(keyword, 0, len(keyword)))


@pytest.mark.parametrize('string, token', [
    keyword_test_case('and', OperatorToken),
    keyword_test_case('as', AsToken),
    keyword_test_case('asc', AscToken),
    keyword_test_case('select', SelectToken),
])
def test_keywords(string, token):
    assert list(tokenize(string)) == [token]


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
