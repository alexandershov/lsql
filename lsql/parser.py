from __future__ import absolute_import, division, print_function, unicode_literals


class Parser(object):
    def __init__(self, tokens):
        self._tokens = list(tokens)
        self._index = 0

    def advance(self):
        self._check_bounds(self._index + 1)
        self._index += 1

    def peek(self):
        return self._tokens[self._index + 1]

    @property
    def token(self):
        return self._tokens[self._index]

    def parse(self):
        return self.expr(left_bp=0)

    def expr(self, left_bp=0):
        token = self.token
        self.advance()
        left = token.prefix(self)
        while self.token.right_bp > left_bp:
            token = self.token
            self.advance()
            left = token.suffix(left, self)
        return left

    def _check_bounds(self, index):
        if index < 0 or index >= len(self._tokens):
            raise IndexError(index, len(self._tokens))


def parse(tokens):
    return Parser(tokens).parse()
