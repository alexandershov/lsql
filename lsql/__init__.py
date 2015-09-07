from __future__ import division, print_function

from collections import OrderedDict
from grp import getgrgid
from pwd import getpwuid
import argparse
import datetime
import operator
import re

from pyparsing import (
    alphas, CaselessKeyword, Group, delimitedList, Optional, QuotedString, Word,
    CharsNotIn, White, nums, Combine, oneOf, sglQuotedString,
    Forward, Suppress)

import os

SIZE_SUFFIXES = {
    'k': 1,
    'kb': 1,
    'm': 2,
    'mb': 2,
    'g': 3,
    'gb': 3,
}


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


class Timestamp(int):
    def __str__(self):
        return datetime.datetime.utcfromtimestamp(self).isoformat()


class Mode(object):
    def __init__(self, mode):
        self.mode = mode

    def __str__(self):
        return oct(self.mode)


class Stat(object):
    ATTRS = OrderedDict.fromkeys([
        'path', 'fullpath', 'dir', 'fulldir', 'extension',
        'name', 'size', 'mode', 'owner', 'group', 'ctime', 'atime', 'mtime',
        'depth', 'type', 'device', 'hardlinks', 'inode',
    ])

    def __init__(self, path, depth):
        self.path = path
        self.depth = depth
        self.__stat = os.lstat(path)

    @property
    def fullpath(self):
        return os.path.normpath(os.path.join(os.getcwd(), self.path))

    @property
    def device(self):
        return self.__stat.st_dev

    @property
    def hardlinks(self):
        return self.__stat.st_nlink

    @property
    def inode(self):
        return self.__stat.st_ino

    @property
    def extension(self):
        extension = os.path.splitext(self.path)[1]
        if extension:
            extension = extension[1:]  # skip dot
        return extension

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def dir(self):
        return os.path.dirname(self.path)

    @property
    def fulldir(self):
        return os.path.dirname(self.fullpath)

    @property
    def owner(self):
        return getpwuid(self.__stat.st_uid).pw_name

    @property
    def group(self):
        return getgrgid(self.__stat.st_gid).gr_name

    @property
    def mode(self):
        return Mode(self.__stat.st_mode)

    @property
    def ctime(self):
        return Timestamp(self.__stat.st_ctime)

    @property
    def mtime(self):
        return Timestamp(self.__stat.st_mtime)

    @property
    def atime(self):
        return Timestamp(self.__stat.st_atime)

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

# matches strings of form 'digits:suffix'. e.g '30kb'
SIZE_RE = re.compile(r'(?P<value>\d+)(?P<suffix>[a-z]+)?$', re.I)


def eval_size_literal(literal):
    match = SIZE_RE.match(literal)
    if not match:
        raise ValueError('bad literal: {!r}'.format(literal))
    value = int(match.group('value'))
    suffix = match.group('suffix')
    if suffix:
        value *= 1024 ** SIZE_SUFFIXES[suffix]
    return value


def eval_value(value, stat):
    if len(value) == 2 and value[0] in FUNCTIONS:  # function call
        return FUNCTIONS[value[0]](eval_value(value[1], stat))
    if value.startswith("'"):
        return value[1:-1]
    if value[0].isdigit():
        return eval_size_literal(value)
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
    stats = []
    limit = int(tokens.limit) if tokens.limit else float('inf')
    for path, depth in walk_with_depth(directory):
        stat = Stat(path, depth)
        if not tokens.condition or eval_condition(tokens.condition, stat):
            stats.append(stat)
        if not tokens.order_by and len(stats) >= limit:
            break
    if tokens.order_by:
        value = tokens.order_by[0]
        reverse = False
        if len(tokens.order_by) == 2:
            reverse = tokens.order_by[-1] == 'DESC'
        order_by = lambda stat: eval_value(value, stat)
    else:
        order_by = lambda stat: 0
        reverse = False
    stats = sorted(stats, key=order_by, reverse=reverse)
    if len(stats) > limit:
        stats = stats[:limit]
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
    literal = Combine(
        Word(nums) + Optional(oneOf('k m g kb mb gb', caseless=True))) | sglQuotedString
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
    limit_clause = CaselessKeyword('LIMIT') + Word(nums).setResultsName('limit')
    return (CaselessKeyword('SELECT') + columns
            + Optional(from_clause)
            + Optional(where_clause)
            + Optional(order_by_clause)
            + Optional(limit_clause))


def main():
    parser = argparse.ArgumentParser(prog='lsql', description='Search for files with SQL')
    parser.add_argument('query', help='sql query to execute, e.g "select name')
    parser.add_argument('directory', help='directory to search in', nargs='?')
    args = parser.parse_args()
    run_query(args.query, args.directory)
