from __future__ import division, print_function

from collections import namedtuple
from itertools import takewhile

KEYWORDS = {'SELECT', 'WHERE'}


class TokenError(Exception):
    pass


class Token(object):
    pass


class Name(Token, namedtuple('Name', ['name'])):
    __slots__ = ()


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
        elif c.isalpha():
            name = []
            while c.isalpha():
                name.append(c)
                c = next(chars, '')
            tokens.append(Name(''.join(name)))
        elif c.isdigit():
            value = []
            while c.isalnum():
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
            tokens.append(Name(c))
            c = next(chars, '')
    return tokens
