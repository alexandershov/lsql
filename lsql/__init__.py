from __future__ import division, print_function

from collections import OrderedDict
from pwd import getpwuid
import argparse
import operator
import re

from pyparsing import (
    alphas, CaselessKeyword, Group, delimitedList, Optional, QuotedString, Word,
    CharsNotIn, White, nums, Combine, oneOf, sglQuotedString,
    Forward, Suppress)

import os


# must be a tuple, because is used as argument to str.endswith
SIZE_SUFFIXES = ('kb', 'mb', 'gb')


def like(string, pattern):
    pattern = re.escape(pattern)
    pattern = pattern.replace(r'\%', '.*').replace(r'\_', '.')
    return re.match(pattern + '$', string)


def rlike(string, re_pattern):
    return bool(re.match(re_pattern + '$', string))


OPERATOR_MAPPING = {
    '=': operator.eq,
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge,
    'like': like,
    'rlike': rlike,
}

FUNCTIONS = {
    'lower': lambda s: s.lower(),
    'upper': lambda s: s.upper(),
    'length': len,
}


class Stat(object):
    ATTRS = OrderedDict.fromkeys([
        'path', 'name', 'size', 'owner', 'ctime', 'atime', 'mtime', 'depth', 'type'])

    def __init__(self, path, depth):
        self.path = path
        self.depth = depth
        self.__stat = os.lstat(path)

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def owner(self):
        return getpwuid(self.__stat.st_uid).pw_name

    @property
    def type(self):
        if os.path.islink(self.path):
            return 'link'
        elif os.path.isdir(self.path):
            return 'dir'
        elif os.path.isfile(self.path):
            return 'file'
        elif os.path.ismount(self.path):
            return 'mount'
        else:
            return 'unknown'

    def get_value(self, name):
        if name not in Stat.ATTRS:
            raise ValueError('unknown attr: {!r}'.format(name))
        return getattr(self, name)

    def __getattr__(self, name):
        return getattr(self.__stat, 'st_' + name)


def eval_size_literal(literal):
    assert literal.endswith(SIZE_SUFFIXES)
    for power, suffix in enumerate(SIZE_SUFFIXES, start=1):
        if literal.endswith(suffix):
            return int(literal[:-len(suffix)]) * (1024 ** power)
    raise ValueError("can't be here")


def eval_value(value, stat):
    if len(value) == 2:  # function call
        return FUNCTIONS[value[0]](eval_value(value[1], stat))
    if value.startswith("'"):
        return value[1:-1]
    if value.endswith(SIZE_SUFFIXES):
        return eval_size_literal(value)
    if value.isdigit():
        return int(value)
    return stat.get_value(value)


def eval_condition(condition, stat):
    return all(eval_simple_condition(c, stat) for c in condition)


def eval_simple_condition(condition, stat):
    good = True
    if condition[0] == 'NOT':
        condition = condition[1:]
        good = False
    left, op, right = condition
    if OPERATOR_MAPPING[op.lower()](eval_value(left, stat), eval_value(right, stat)):
        return good
    return not good


def run_query(query, directory):
    grammar = get_grammar()
    tokens = grammar.parseString(query, parseAll=True)
    if tokens.columns == '*':
        columns = list(Stat.ATTRS)
    else:
        columns = list(tokens.columns)
    if tokens.directory and directory:
        raise ValueError("You can't specify both FROM clause and "
                         "directory as command line argument")
    directory = directory or tokens.directory or '.'
    if not os.path.isdir(directory):
        raise ValueError('{!r} is not a directory'.format(directory))
    print('\t'.join(columns))
    stats = []
    for path, depth in walk_with_depth(directory):
        stat = Stat(path, depth)
        if not tokens.condition or eval_condition(tokens.condition, stat):
            stats.append(stat)
    if tokens.order_by:
        value = tokens.order_by[0]
        reverse = False
        if len(tokens.order_by) == 2:
            reverse = tokens.order_by[-1] == 'DESC'
        order_by = lambda stat: eval_value(value, stat)
    else:
        order_by = lambda stat: 0
        reverse=False
    stats = sorted(stats, key=order_by, reverse=reverse)
    for stat in stats:
        fields = [str(stat.get_value(column)) for column in columns]
        print('\t'.join(fields))


def walk_with_depth(path, depth=0):
    names = os.listdir(path)
    dirs = []
    for name in names:
        full_path = os.path.join(path, name)
        if os.path.isdir(full_path):
            dirs.append(full_path)
        yield full_path, depth
    for d in dirs:
        if not os.path.islink(d):
            for x in walk_with_depth(d, depth + 1):
                yield x


def get_grammar():
    column = Word(alphas)
    bin_op = oneOf('= < <= > >= LIKE RLIKE', caseless=True)
    literal = Combine(Word(nums) + Optional(oneOf('kb mb gb', caseless=True))) | sglQuotedString
    columns = (Group(delimitedList(column)) | '*').setResultsName('columns')
    directory = White() + CharsNotIn('" ').setResultsName('directory')
    from_clause = (CaselessKeyword('FROM')
                   + (QuotedString('"').setResultsName('directory') | directory))
    funcall = Forward()
    value = funcall | column | literal
    funcall << Group(Word(alphas) + Suppress('(') + value + Suppress(')'))
    condition = Group(Optional(CaselessKeyword('NOT')) + value + bin_op + value)
    conditions = Group(delimitedList(condition, delim=CaselessKeyword('AND')))
    where_clause = CaselessKeyword('WHERE') + conditions.setResultsName('condition')
    order_by_clause = (CaselessKeyword('ORDER BY')
                       + Group(
        value + Optional(CaselessKeyword('ASC') | CaselessKeyword('DESC'))).setResultsName(
        'order_by'))
    return (CaselessKeyword('SELECT') + columns
            + Optional(from_clause)
            + Optional(where_clause)
            + Optional(order_by_clause))


def main():
    parser = argparse.ArgumentParser(prog='lsql', description='Search for files with SQL')
    parser.add_argument('query', help='sql query to execute, e.g "select name')
    parser.add_argument('directory', help='directory to search in', nargs='?')
    args = parser.parse_args()
    run_query(args.query, args.directory)
