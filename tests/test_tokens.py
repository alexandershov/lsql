from __future__ import division, print_function, unicode_literals


from lsql.tokens import tokenize, NameToken, SelectToken


def test_simple():
    assert list(tokenize('SELECT path')) == [SelectToken('SELECT'), NameToken('path')]


def test_where():
    pass


def test_number_literal():
    pass


def test_from():
    pass


def test_ge():
    pass


def test_funcall():
    pass
