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

KEYWORDS = {
    'FROM': FROM,
    'SELECT': SELECT,
    'WHERE': WHERE,
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
        elif tokens and isinstance(tokens[-1], Name) and tokens[-1].name == 'FROM' and c != "'":
            value = []
            while not c.isspace():
                value.append(c)
                c = next(chars, '')
                if not c:
                    break
            tokens.append(StringLiteral(''.join(value)))
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
            tokens.append(Name(''.join(name)))
    return tokens


def is_identifier_start(c):
    return c.isalpha() or c.isdigit()


def is_identifier(c):
    return c.isalpha() or c.isdigit() or c == '_'
