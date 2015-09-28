from __future__ import division, print_function, unicode_literals

from lsql.tokens import tokenize, Name, IntLiteral, StringLiteral


def test_simple():
    assert tokenize('SELECT name') == [Name('SELECT'), Name('name')]


def test_where():
    assert tokenize("SELECT name WHERE extension = 'py'") == \
           [Name('SELECT'), Name('name'), Name('WHERE'), Name('extension'),
            Name('='), StringLiteral('py')]


def test_number_literal():
    assert tokenize('SELECT name WHERE size > 3kb') == \
           [Name('SELECT'), Name('name'), Name('WHERE'), Name('size'),
            Name('>'), IntLiteral('3kb')]


def test_from():
    assert tokenize('SELECT name FROM ./tmp') == \
        [Name('SELECT'), Name('name'), Name('FROM'), StringLiteral('./tmp')]
