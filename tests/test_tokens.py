from __future__ import division, print_function, unicode_literals

from lsql.tokens import (
    tokenize, Name, IntLiteral, StringLiteral,
    FROM, SELECT, WHERE, EQ, GT, GE, LPAREN, PLUS, COMMA, RPAREN,
)


def test_simple():
    assert tokenize('SELECT name') == [SELECT, Name('name')]


def test_where():
    assert tokenize("SELECT name WHERE extension = 'py'") == \
           [SELECT, Name('name'), WHERE, Name('extension'),
            EQ, StringLiteral('py')]


def test_number_literal():
    assert tokenize('SELECT name WHERE size > 3kb') == \
           [SELECT, Name('name'), WHERE, Name('size'),
            GT, IntLiteral('3kb')]


def test_from():
    assert tokenize('SELECT name FROM ./tmp') == \
           [SELECT, Name('name'), FROM, StringLiteral('./tmp')]


def test_ge():
    assert tokenize('SELECT name WHERE size >= 20') == \
           [SELECT, Name('name'), WHERE, Name('size'), GE, IntLiteral('20')]


def test_funcall():
    assert tokenize('SELECT 1day+age(ctime, CURRENT_DATE)') == \
           [SELECT, IntLiteral('1day'), PLUS, Name('age'),
            LPAREN, Name('ctime'), COMMA, Name('CURRENT_DATE'), RPAREN]
