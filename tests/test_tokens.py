from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from lsql.tokens import (
    NameToken, OperatorToken, Position, SelectToken, tokenize,
)


@pytest.mark.parametrize('string, token', [
    ('and', OperatorToken('and', Position('and', 0, 3))),
    ('select', SelectToken('select', Position('select', 0, 6)))
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
