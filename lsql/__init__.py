from __future__ import division, print_function

from collections import OrderedDict
from functools import wraps
from grp import getgrgid
from pwd import getpwuid
from stat import S_IXUSR
import argparse
import datetime
import errno
import operator
import os
import re
import sys

from colorama import Fore, init
from pyparsing import (
    alphas, CaselessKeyword, Group, delimitedList, Optional, QuotedString, Word,
    nums, Combine, oneOf, sglQuotedString,
    Forward, Suppress,
)

CURRENT_TIME = datetime.datetime.utcnow()
CURRENT_DATE = CURRENT_TIME.date()

KILO = 1024
MEGA = KILO * 1024
GIGA = MEGA * 1024

# unit -> num of bytes in 1 unit
SIZE_SUFFIXES = {
    'k': KILO,
    'kb': KILO,
    'm': MEGA,
    'mb': MEGA,
    'g': GIGA,
    'gb': GIGA,
    'minute': 60,
    'minutes': 60,
    'hour': 3600,
    'hours': 3600,
    'day': 86400,
    'days': 86400,
    'week': 86400 * 7,
    'weeks': 86400 * 7,
    'month': 86400 * 30,
    'months': 86400 * 30,
}


class Error(Exception):
    pass


class Null(object):
    def __str__(self):
        return 'NULL'

    def __nonzero__(self):
        return False


NULL = Null()


def like(string, pattern):
    pattern = re.escape(pattern)
    pattern = pattern.replace(r'\%', '.*').replace(r'\_', '.')
    return rlike(string, pattern)


def rlike(string, re_pattern):
    # we need re.DOTALL because string can contain newlines (e.g in 'text' column)
    regex = re.compile(re_pattern + '$', re.DOTALL)
    if not isinstance(string, list):
        string = [string]
    return any(regex.match(line) for line in string)


def age(ts):
    d_time = datetime.datetime.utcfromtimestamp(ts)
    return Interval.from_range(d_time, CURRENT_TIME)


class Interval(int):
    @classmethod
    def from_range(cls, start, end):
        return cls((end - start).total_seconds())

    def __str__(self):
        parts = [(86400, 'days'), (3600, 'hours'), (60, 'minutes'), (1, 'seconds')]
        human = []
        seconds = int(self)
        for n, name in parts:
            if seconds:
                x, seconds = divmod(seconds, n)
                if x:
                    human.append('{} {}'.format(x, name))
        return ', '.join(human)


def btrim(string, chars=None):
    return string.strip(chars)


def propagate_null(fn):
    @wraps(fn)
    def wrapper(*args):
        if any(arg is NULL for arg in args):
            return NULL
        return fn(*args)

    return wrapper


def map_values(function, dictionary):
    return {key: function(value) for key, value in dictionary.viewitems()}


OPERATOR_MAPPING = map_values(propagate_null, {
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
})

FUNCTIONS = map_values(propagate_null, {
    'lower': lambda s: s.lower(),
    'upper': lambda s: s.upper(),
    'length': len,
    'age': age,
    'btrim': btrim,
})


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
        'text', 'lines', 'is_executable'
    ])

    ATTR_ALIASES = {
        '*': 'path',
        'ext': 'extension',
        'is_exec': 'is_executable'
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
        return extension[1:]  # skip dot

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
            raise Error('birthtime is not supported on your platform')
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
    def text(self):
        if self.type == 'dir':
            return NULL
        with open(self.path, 'rb') as fileobj:
            return fileobj.read()

    @property
    def lines(self):
        content = self.text
        if content is NULL:
            return NULL
        return content.splitlines()

    def get_value(self, name):
        name = Stat.ATTR_ALIASES.get(name, name)
        if name not in Stat.ATTRS:
            raise Error('unknown column: {!r}'.format(name))
        return getattr(self, name)

    @property
    def is_executable(self):
        return bool(self.__stat.st_mode & S_IXUSR)

    def get_tags(self):
        tags = set()
        if self.is_executable:
            tags.add('exec')
        tags.add(self.type)
        return tags

# matches strings of form 'digits:suffix'. e.g '30kb'
SIZE_RE = re.compile(r'(?P<value>\d+)(?P<suffix>[a-z]+)?$', re.I)


def eval_size_literal(literal):
    match = SIZE_RE.match(literal)
    if not match:
        raise Error('bad literal: {!r}'.format(literal))
    value = int(match.group('value'))
    suffix = match.group('suffix')
    if suffix:
        value *= SIZE_SUFFIXES[suffix]
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
    if len(condition) == 1:
        return modify(eval_value(condition[0], stat))
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
    columns = list(tokens.columns) or ['path']
    if tokens.directory and directory:
        raise Error("You can't specify both FROM clause and "
                    "directory as command line argument")
    directory = directory or tokens.directory or '.'
    if not os.path.isdir(directory):
        raise Error('{!r} is not a directory'.format(directory))
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
        order_by = lambda st: eval_value(value, st)
    else:
        order_by = lambda st: 0
        reverse = False
    stats = sorted(stats, key=order_by, reverse=reverse)
    if len(stats) > limit:
        stats = stats[:limit]
    for stat in stats:
        fields = []
        for column in columns:
            value = str(eval_value(column, stat))
            if column in Stat.COLORED_ATTRS:
                tags = stat.get_tags()
                color = Fore.RESET
                for tag, color in colors.viewitems():
                    if tag in tags:
                        break
                fields.append(colored(value, color))
            else:
                fields.append(value)
        yield fields
    if forbidden:
        if verbose:
            print_warning('Skipped paths because of permissions:')
            for path in forbidden:
                print_warning(path)
        else:
            print_warning('{:d} paths were skipped because of permissions'.format(
                len(forbidden)))
            print_warning('use -v (or --verbose) flag to show skipped paths')


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
    ident = alphas + '_'
    column = Word(ident)
    literal = Combine(
        Word(nums) + Optional(oneOf(' '.join(SIZE_SUFFIXES),
                                    caseless=True))) | sglQuotedString
    funcall = Forward()
    value = funcall | column | literal
    funcall << Group(Word(ident) + Suppress('(') + Group(delimitedList(value)) + Suppress(')'))
    bin_op = oneOf('<> != = == < <= > >= LIKE RLIKE', caseless=True)

    columns = (Group(delimitedList(value)) | '*').setResultsName('columns')
    from_clause = (CaselessKeyword('FROM')
                   + QuotedString("'").setResultsName('directory'))
    condition = Group(Optional(CaselessKeyword('NOT')) + value + bin_op + value) | Group(value)
    conditions = Group(delimitedList(condition, delim=CaselessKeyword('AND')))
    where_clause = CaselessKeyword('WHERE') + conditions.setResultsName('condition')
    order_by_clause = (CaselessKeyword('ORDER BY')
                       + Group(
        value + Optional(CaselessKeyword('ASC') | CaselessKeyword('DESC'))).setResultsName(
        'order_by'))
    limit_clause = CaselessKeyword('LIMIT') + Word(nums).setResultsName('limit')
    select_clause = CaselessKeyword('SELECT') + columns
    return (Optional(select_clause)
            + Optional(from_clause)
            + Optional(where_clause)
            + Optional(order_by_clause)
            + Optional(limit_clause))


def main():
    args = parse_args()
    init()
    try:
        for row in run_query(args.query, args.directory, args.header, args.verbose):
            print('\t'.join(row))
    except Error as exc:
        print_error(str(exc))
        sys.exit(1)


def print_warning(text):
    print(colored(text, Fore.RED), file=sys.stderr)


def print_error(text):
    print_warning(text)


def colored(text, color):
    return color + text + Fore.RESET


# TODO: respect background, respect executable
def parse_lscolors(lscolors):
    """
    :param lscolors: value of $LSCOLORS env var
    :return: dictionary {tag -> color}
    """
    if not lscolors:
        return OrderedDict([
            ('dir', Fore.RESET),
            ('link', Fore.RESET),
            ('exec', Fore.RESET),
            ('file', Fore.RESET),
        ])
    return OrderedDict([
        ('dir', lscolor_to_termcolor(lscolors[0].lower())),
        ('link', lscolor_to_termcolor(lscolors[2].lower())),
        ('exec', lscolor_to_termcolor(lscolors[8].lower())),
        ('file', Fore.RESET),
    ])


BROWN = '\x1b[33m'


def lscolor_to_termcolor(lscolor):
    color_mapping = {
        'a': Fore.BLACK,
        'b': Fore.RED,
        'c': Fore.GREEN,
        'd': Fore.RESET,
        'e': BROWN,
        'f': Fore.MAGENTA,
        'g': Fore.CYAN,
        'h': Fore.LIGHTWHITE_EX,
    }
    return color_mapping.get(lscolor, Fore.RESET)


def parse_args():
    parser = argparse.ArgumentParser(prog='lsql', description='Search for files with SQL')
    parser.add_argument('-H', '--header', action='store_true',
                        help='Show header with column names?')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='verbose mode')
    parser.add_argument('query', help='sql query to execute, e.g "select name',
                        default='', nargs='?')
    parser.add_argument('directory', help='directory to search in', nargs='?')
    return parser.parse_args()
