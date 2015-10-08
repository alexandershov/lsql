from __future__ import division, print_function

from collections import namedtuple

OPERATORS = {'>', '<', '=', '>=', '<=', '||', '<>', '!=',
             '+', '-', '*', '/',
             ',', '(', ')',
             }


class TokenError(Exception):
    pass


class Token(object):
    pass


class Name(Token, namedtuple('Name', ['name'])):
    __slots__ = ()


SELECT = Name('SELECT')
WHERE = Name('WHERE')
FROM = Name('FROM')
GT = Name('>')
LT = Name('<')
EQ = Name('=')
GE = Name('>=')
LE = Name('<=')
CONCAT = Name('||')
NE_OLD = Name('<>')
NE_NEW = Name('!=')
PLUS = Name('+')
MINUS = Name('-')
MUL = Name('*')
DIV = Name('/')
COMMA = Name(',')
LPAREN = Name('(')
RPAREN = Name(')')

KEYWORDS = {
    name.name: name for name in
    [SELECT, WHERE, FROM, GT, LT, EQ, GE, LE, CONCAT, NE_OLD, NE_NEW, PLUS, MINUS, MUL,
     DIV, COMMA, LPAREN, RPAREN]
    }


class StringLiteral(Token, namedtuple('StringLiteral', ['value'])):
    __slots__ = ()


class IntLiteral(Token, namedtuple('IntLiteral', ['value'])):
    __slots__ = ()


def tokenize(s):
    tokens = []
    s = unicode(s)
    chars = iter(s)
    c = next(chars, '')
    while c:
        if c.isspace():
            while c.isspace():
                c = next(chars, '')
        elif is_identifier_start(c):
            name = []
            while is_identifier(c):
                name.append(c)
                c = next(chars, '')
            name = ''.join(name)
            if name.upper() in KEYWORDS:
                tokens.append(KEYWORDS[name.upper()])
            else:
                tokens.append(Name(''.join(name)))
        elif c.isdigit():
            value = []
            while is_identifier(c):
                value.append(c)
                c = next(chars, '')
            tokens.append(IntLiteral(''.join(value)))
        elif c == "'":
            value = []
            c = next(chars, '')
            while c != "'":
                if not c:
                    raise TokenError('unclosed single quote')
                value.append(c)
                c = next(chars, '')
            tokens.append(StringLiteral(''.join(value)))
            c = next(chars, '')
        else:
            name = [c]
            while (''.join(name) in OPERATORS) and c:
                c = next(chars, '')
                name.append(c)
            if c:
                name = name[:-1]
            if not name:
                raise TokenError('unknown char: {}'.format(c))
            tokens.append(KEYWORDS[''.join(name)])
    return tokens


def is_identifier_start(c):
    return c.isalpha() or c == '_'


def is_identifier(c):
    return is_identifier_start(c) or c.isdigit()
