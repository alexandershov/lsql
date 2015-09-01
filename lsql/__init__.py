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
}


class Stat(object):
    ATTRS = OrderedDict.fromkeys(['path', 'name', 'size', 'owner', 'ctime'])

    def __init__(self, path):
        self.path = path
        self.__stat = os.lstat(path)

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def owner(self):
        return getpwuid(self.__stat.st_uid).pw_name

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
    for dirpath, dirnames, filenames in os.walk(directory):
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = Stat(path)
            if not tokens.condition or eval_condition(tokens.condition, stat):
                stats.append(stat)
    if tokens.order_by:
        order_by = lambda stat: eval_value(tokens.order_by, stat)
    else:
        order_by = lambda stat: 0
    stats = sorted(stats, key=order_by)
    for stat in stats:
        fields = [str(stat.get_value(column)) for column in columns]
        print('\t'.join(fields))



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
    order_by_clause = CaselessKeyword('ORDER BY') + value.setResultsName('order_by')
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
