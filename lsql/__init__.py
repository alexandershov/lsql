from __future__ import division, print_function

from collections import OrderedDict
from pwd import getpwuid
import argparse
import operator

from pyparsing import (
    alphas, CaselessKeyword, Group, delimitedList, Optional, QuotedString, Word,
    CharsNotIn, White, nums, Combine, oneOf,
)

import os

OPERATOR_MAPPING = {
    '=': operator.eq,
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge,
}

# must be tuple, because is used as argument to str.endswith
SIZE_SUFFIXES = ('kb', 'mb', 'gb')



class Stat(object):
    ATTRS = OrderedDict.fromkeys(['path', 'name', 'size', 'owner', 'ctime'])

    def __init__(self, path):
        self.path = path
        self.__stat = os.stat(path)

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


def eval_literal(literal):
    if literal.endswith(SIZE_SUFFIXES):
        return eval_size_literal(literal)
    return int(literal)


def eval_condition(condition, stat):
    column, op, literal = condition
    if OPERATOR_MAPPING[op](stat.get_value(column), eval_literal(literal)):
        return True


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
    for dirpath, dirnames, filenames in os.walk(directory):
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = Stat(path)
            if tokens.condition and eval_condition(tokens.condition, stat):
                fields = [str(stat.get_value(column)) for column in columns]
                print('\t'.join(fields))


def get_grammar():
    column = Word(alphas)
    bin_op = oneOf('= < <= > >=', caseless=True)
    int_literal = Combine(Word(nums) + Optional(oneOf('kb mb gb', caseless=True)))
    columns = (Group(delimitedList(column)) | '*').setResultsName('columns')
    directory = White() + CharsNotIn('" ').setResultsName('directory')
    from_clause = (CaselessKeyword('FROM')
                   + (QuotedString('"').setResultsName('directory') | directory))
    where_clause = (CaselessKeyword('WHERE')
                    + (column + bin_op + int_literal).setResultsName('condition'))
    return (CaselessKeyword('SELECT') + columns
            + Optional(from_clause)
            + Optional(where_clause))


def main():
    parser = argparse.ArgumentParser(prog='lsql', description='Search for files with SQL')
    parser.add_argument('query', help='sql query to execute, e.g "select name')
    parser.add_argument('directory', help='directory to search in', nargs='?')
    args = parser.parse_args()
    run_query(args.query, args.directory)
