from __future__ import division, print_function

from collections import OrderedDict
from grp import getgrgid
from pwd import getpwuid
import argparse
import datetime
import errno
import operator
import os
import re
import sys

from pyparsing import (
    alphas, CaselessKeyword, Group, delimitedList, Optional, QuotedString, Word,
    CharsNotIn, White, nums, Combine, oneOf, sglQuotedString,
    Forward, Suppress,
)
from colorama import Fore, init

CURRENT_DATE = datetime.datetime.combine(datetime.datetime.now().date(), datetime.time())

SIZE_SUFFIXES = {
    'k': 1,
    'kb': 1,
    'm': 2,
    'mb': 2,
    'g': 3,
    'gb': 3,
}

NULL = object()


def like(string, pattern):
    pattern = re.escape(pattern)
    pattern = pattern.replace(r'\%', '.*').replace(r'\_', '.')
    return rlike(string, pattern)


def rlike(string, re_pattern):
    if string is NULL:
        return False
    # we need re.DOTALL because string can contain newlines (e.g in 'content' column)
    regex = re.compile(re_pattern + '$', re.DOTALL)
    if not isinstance(string, list):
        string = [string]
    return any(regex.match(line) for line in string)


def age(ts):
    d_time = datetime.datetime.utcfromtimestamp(ts)
    return Interval((CURRENT_DATE - d_time).total_seconds())


class Interval(object):
    def __init__(self, seconds):
        self.seconds = int(seconds)

    def __str__(self):
        parts = [(86400, 'days'), (3600, 'hours'), (60, 'minutes'), (1, 'seconds')]
        human = []
        seconds = self.seconds
        for n, name in parts:
            if seconds:
                x, seconds = divmod(seconds, n)
                if x:
                    human.append('{} {}'.format(x, name))
        return ', '.join(human)


def btrim(string, chars=None):
    return string.strip(chars)


OPERATOR_MAPPING = {
    '<>': operator.ne,
    '!=': operator.ne,
    '=': operator.eq,
    '==': operator.eq,
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
    'age': age,
    'btrim': btrim,
}


class Timestamp(int):
    def __str__(self):
        return datetime.datetime.fromtimestamp(self).isoformat()


class Mode(object):
    def __init__(self, mode):
        self.mode = mode

    def __str__(self):
        return oct(self.mode)


class Stat(object):
    ATTRS = OrderedDict.fromkeys([
        'fullpath', 'size', 'owner',
        'path', 'fulldir', 'dir', 'name', 'extension',
        'mode', 'group', 'atime', 'mtime', 'ctime', 'birthtime',
        'depth', 'type', 'device', 'hardlinks', 'inode',
        'content', 'lines',
    ])

    ATTR_ALIASES = {
        '*': 'path',
    }

    COLORED_ATTRS = {'name', 'path', 'fullpath', '*'}

    def __init__(self, path, depth):
        self.path = path
        self.depth = depth
        self.__stat = os.lstat(path)

    @property
    def fullpath(self):
        return os.path.normpath(os.path.join(os.getcwd(), self.path))

    @property
    def size(self):
        if self.type == 'dir':
            return get_dir_size(self.path)
        return self.__stat.st_size

    @property
    def owner(self):
        return getpwuid(self.__stat.st_uid).pw_name

    @property
    def fulldir(self):
        return os.path.dirname(self.fullpath)

    @property
    def dir(self):
        return os.path.dirname(self.path)

    @property
    def name(self):
        return os.path.basename(self.path)

    @property
    def extension(self):
        extension = os.path.splitext(self.path)[1]
        if extension:
            extension = extension[1:]  # skip dot
        return extension

    @property
    def mode(self):
        return Mode(self.__stat.st_mode)

    @property
    def group(self):
        return getgrgid(self.__stat.st_gid).gr_name

    @property
    def atime(self):
        return Timestamp(self.__stat.st_atime)

    @property
    def mtime(self):
        return Timestamp(self.__stat.st_mtime)

    @property
    def ctime(self):
        return Timestamp(self.__stat.st_ctime)

    @property
    def birthtime(self):
        if not hasattr(self.__stat, 'st_birthtime'):
            raise ValueError('birthtime is not supported on your platform')
        return Timestamp(self.__stat.st_birthtime)

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
    def content(self):
        if self.type == 'dir':
            return NULL
        with open(self.path, 'rb') as input:
            return input.read()

    @property
    def lines(self):
        return self.content.splitlines()

    def get_value(self, name):
        name = Stat.ATTR_ALIASES.get(name, name)
        if name not in Stat.ATTRS:
            raise ValueError('unknown attr: {!r}'.format(name))
        return getattr(self, name)

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
    if len(value) == 2 and value[0].lower() in FUNCTIONS:  # function call
        args = [eval_value(x, stat) for x in value[1]]
        return FUNCTIONS[value[0].lower()](*args)
    if value.startswith("'"):
        return value[1:-1]
    if value[0].isdigit():
        return eval_size_literal(value)
    return stat.get_value(value)


def eval_condition(condition, stat):
    return all(eval_simple_condition(c, stat) for c in condition)


def eval_simple_condition(condition, stat):
    modify = identity
    if condition[0] == 'NOT':
        condition = condition[1:]
        modify = operator.not_
    left, op, right = condition
    if OPERATOR_MAPPING[op.lower()](eval_value(left, stat), eval_value(right, stat)):
        return modify(True)
    return modify(False)


def identity(x):
    return x


def run_query(query, directory=None, header=False, verbose=False):
    colors = parse_lscolors(os.getenv('LSCOLORS') or '')
    grammar = get_grammar()
    tokens = grammar.parseString(query, parseAll=True)
    columns = list(tokens.columns)
    if tokens.directory and directory:
        raise ValueError("You can't specify both FROM clause and "
                         "directory as command line argument")
    directory = directory or tokens.directory or '.'
    if not os.path.isdir(directory):
        raise ValueError('{!r} is not a directory'.format(directory))
    if header:
        yield columns
    stats = []
    limit = int(tokens.limit) if tokens.limit else float('inf')
    forbidden = []
    for path, depth in walk_with_depth(directory, forbidden=forbidden):
        path = os.path.relpath(path, os.getcwd())
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
        fields = []
        for column in columns:
            value = str(eval_value(column, stat))
            if column in Stat.COLORED_ATTRS:
                color = colors.get(stat.type, Fore.RESET)
                fields.append(colored(value, color))
            else:
                fields.append(value)
        yield fields
    if forbidden:
        if verbose:
            warning('Skipped paths because of permissions:')
            for path in forbidden:
                warning(path)
        else:
            warning('{:d} paths were skipped because of permissions'.format(
                len(forbidden)))
            warning('use -v (or --verbose) flag to show skippped paths')


def walk_with_depth(path, depth=0, forbidden=[]):
    try:
        names = os.listdir(path)
    except OSError as exc:
        if exc.errno == errno.EACCES:
            forbidden.append(path)
        return
    dirs = []
    for name in names:
        full_path = os.path.join(path, name)
        if os.path.isdir(full_path):
            dirs.append(full_path)
        yield full_path, depth
    for d in dirs:
        if not os.path.islink(d):
            for x in walk_with_depth(d, depth + 1, forbidden):
                yield x


def get_dir_size(path):
    size = 0
    for path, _ in walk_with_depth(path):
        if os.path.isfile(path):
            size += os.lstat(path).st_size
    return size


def get_grammar():
    column = Word(alphas)
    literal = Combine(
        Word(nums) + Optional(oneOf('k m g kb mb gb', caseless=True))) | sglQuotedString
    funcall = Forward()
    value = funcall | column | literal
    funcall << Group(Word(alphas) + Suppress('(') + Group(delimitedList(value)) + Suppress(')'))
    bin_op = oneOf('<> != = == < <= > >= LIKE RLIKE', caseless=True)

    columns = (Group(delimitedList(value)) | '*').setResultsName('columns')
    from_clause = (CaselessKeyword('FROM')
                   + QuotedString("'").setResultsName('directory'))
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
    args = parse_args()
    init()
    for row in run_query(args.query, args.directory, args.header, args.verbose):
        print('\t'.join(row))


def warning(text):
    print(colored(text, Fore.RED), file=sys.stderr)


def colored(text, color):
    return color + text + Fore.RESET


# TODO: respect background, respect executable
def parse_lscolors(lscolors):
    """
    :param lscolors: value of $LSCOLORS env var
    :return: dictionary {file_type -> color}
    """
    if not lscolors:
        return {
            'dir': Fore.RESET,
            'file': Fore.RESET,
            'link': Fore.RESET,
        }
    return {
        'dir': lscolor_to_term(lscolors[0].lower()),
        'file': Fore.RESET,
        'link': lscolor_to_term(lscolors[2].lower()),
    }


def lscolor_to_term(s):
    mapping = {
        'a': Fore.BLACK,
        'b': Fore.RED,
        'c': Fore.GREEN,
        'd': Fore.RESET,
        'e': Fore.BLUE,  # should be brown
        'f': Fore.MAGENTA,
        'g': Fore.CYAN,
        'h': Fore.LIGHTWHITE_EX,
    }
    return mapping.get(s, Fore.RESET)


def parse_args():
    parser = argparse.ArgumentParser(prog='lsql', description='Search for files with SQL')
    parser.add_argument('-H', '--header', action='store_true',
                        help='Show header with column names?')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose mode')
    parser.add_argument('query', help='sql query to execute, e.g "select name')
    parser.add_argument('directory', help='directory to search in', nargs='?')
    return parser.parse_args()
