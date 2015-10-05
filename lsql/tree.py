from __future__ import division, print_function

from functools import wraps
import operator
import re

from lsql import walk_with_depth, Stat


def sql_function(fn):
    @wraps(fn)
    def wrapped(x, y):
        if x is None or y is None:
            return None
        return fn(x, y)

    return wrapped


def like(string, pattern):
    pattern = re.escape(pattern)
    pattern = pattern.replace(r'\%', '.*').replace(r'\_', '.')
    return rlike(string, pattern)


def rlike(string, re_pattern):
    # we need re.DOTALL because string can contain newlines (e.g in 'content' column)
    regex = re.compile(re_pattern + '$', re.DOTALL)
    if not isinstance(string, list):
        string = [string]
    return any(regex.match(line) for line in string)


FUNCTIONS = {
    '<>': sql_function(operator.ne),
    '!=': sql_function(operator.ne),
    '=': sql_function(operator.eq),
    '==': sql_function(operator.eq),
    '<': sql_function(operator.lt),
    '<=': sql_function(operator.le),
    '>': sql_function(operator.gt),
    '>=': sql_function(operator.ge),
    'like': sql_function(like),
    'rlike': sql_function(rlike),
    'lower': sql_function(lambda s: s.lower()),
    'upper': sql_function(lambda s: s.upper()),
    'length': sql_function(len),
    # 'age': sql_function(age),  TODO
    # 'btrim': sql_function(btrim), TODO
}


class Node(object):
    def eval(self, context):
        raise NotImplementedError


class LiteralNode(Node):
    def __init__(self, value):
        self.value = value

    def eval(self, context):
        return self.value


class FunctionNode(Node):
    def __init__(self, function, args):
        self.function = function
        self.args = args

    def eval(self, context):
        args = [arg.eval(context) for arg in self.args]
        return self.function(args)


class OrNode(Node):
    def __init__(self, args):
        self.args = args

    def eval(self, context):
        return any(arg.eval(context) for arg in self.args)


class AndNode(Node):
    def __init__(self, args):
        self.args = args

    def eval(self, context):
        return all(arg.eval(context) for arg in self.args)


class NameNode(Node):
    def __init__(self, name):
        self.name = name

    def eval(self, context):
        return context.get_value(self.name)


class FromNode(Node):
    def __init__(self, path):
        self.path = path

    def eval(self, context):
        for path, depth in walk_with_depth(self.path):
            yield Stat(path, depth)


class WhereNode(Node):
    def __init__(self, condition):
        self.condition = condition

    def eval(self, context):
        return self.condition.eval(context)


class AlwaysTrueWhereNode(Node):
    def eval(self, context):
        return True


class SelectNode(Node):
    def __init__(self, expressions, from_clause, where_clause=AlwaysTrueWhereNode()):
        self.expressions = expressions
        self.from_clause = from_clause
        self.where_clause = where_clause

    def eval(self, context):
        stats = self.from_clause.eval(context)
        for stat in stats:
            if self.where_clause.eval(stat):
                row = []
                for expr in self.expressions:
                    row.append(expr.eval(stat))
                yield row
