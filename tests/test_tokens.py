from __future__ import division, print_function, unicode_literals

from lsql.tokens import tokenize, Name, IntLiteral, StringLiteral, FROM, SELECT, WHERE


def test_simple():
    assert tokenize('SELECT name') == [SELECT, Name('name')]


def test_where():
    assert tokenize("SELECT name WHERE extension = 'py'") == \
           [SELECT, Name('name'), WHERE, Name('extension'),
            Name('='), StringLiteral('py')]


def test_number_literal():
    assert tokenize('SELECT name WHERE size > 3kb') == \
           [SELECT, Name('name'), WHERE, Name('size'),
            Name('>'), IntLiteral('3kb')]


def test_from():
    assert tokenize('SELECT name FROM ./tmp') == \
        [SELECT, Name('name'), FROM, StringLiteral('./tmp')]


def test_ge():
    assert tokenize('SELECT name WHERE size >= 20') == \
        [SELECT, Name('name'), WHERE, Name('size'), Name('>='), IntLiteral('20')]
