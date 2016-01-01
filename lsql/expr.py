from __future__ import absolute_import, division, print_function, unicode_literals

import numbers
from collections import namedtuple, OrderedDict, Sized
from datetime import datetime
from functools import wraps
from grp import getgrgid
from pwd import getpwuid
from stat import S_IXUSR
import errno
import os

# TODO(aershov182): maybe inherit from `dict`?
import operator


class Context(object):
    """
    Case-insensitive context.
    """

    def __init__(self, items):
        """
        :param items: dictionary str -> value
        """
        self._items = items

    def __getitem__(self, item):
        item = item.lower()
        return self._items[item]

    def __repr__(self):
        return 'Context(items={!r})'.format(self._items)


class Null(object):
    def __repr__(self):
        return 'NULL'


NULL = Null()

_CURRENT_TIME = datetime.utcnow()
_CURRENT_DATE = _CURRENT_TIME.date()


def get_dir_size(path):
    size = 0
    for path, _ in walk_with_depth(path):
        if os.path.isfile(path):
            size += os.lstat(path).st_size
    return size


class Timestamp(int):
    def __str__(self):
        return datetime.datetime.fromtimestamp(self).isoformat()


class Stat(object):
    ATTRS = OrderedDict.fromkeys([
        'fullpath', 'size', 'owner',
        'path', 'fulldir', 'dir', 'name', 'extension', 'no_ext',
        'mode', 'group', 'atime', 'mtime', 'ctime', 'birthtime',
        'depth', 'type', 'device', 'hardlinks', 'inode',
        'text', 'lines', 'is_executable'
    ])

    ATTR_ALIASES = {
        'ext': 'extension',
        'is_exec': 'is_executable',
    }

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
    def no_ext(self):
        return os.path.splitext(self.name)[0]

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
            raise ExprError('birthtime is not supported on your platform')
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
        text = self.text
        if text is NULL:
            return NULL
        return text.splitlines()

    def __getitem__(self, item):
        name = Stat.ATTR_ALIASES.get(item, item)
        if name not in Stat.ATTRS:
            raise KeyError('unknown column: {!r}'.format(name))
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

    @classmethod
    def get_type(cls):
        # TODO(aershov182): maybe create Scope class (that is the same as Context?)
        return Context({
            'fullpath': unicode,
            'size': int,
            'owner': unicode,
            'path': unicode,
            'fulldir': unicode,
            'dir': unicode,
            'name': unicode,
            'extension': unicode,
            'no_ext': unicode,
            'mode': unicode,
            'group': unicode,
            'atime': int,
            'mtime': int,
            'ctime': int,
            'birthtime': int,
            'depth': int,
            'type': unicode,
            'device': unicode,
            'hardlinks': int,
            'inode': unicode,
            'text': unicode,
            'lines': Sized,
            'is_executable': bool,
            'ext': unicode,
            'is_exec': unicode,
        })


def _files_table_function(directory):
    for path, depth in walk_with_depth(directory):
        path = os.path.relpath(path, os.getcwd())
        yield Stat(path, depth)


_files_table_function.return_type = Stat.get_type()


def sql_function(function, signature):
    @wraps(function)
    def wrapper(*args):
        for arg in args:
            if arg is NULL:
                return NULL
        return function(*args)

    wrapper.return_type = signature[-1]
    return wrapper


# TODO(aershov182): probably we don't need to prefix private names with underscore
BUILTIN_CONTEXT = Context({
    'null': NULL,
    'current_time': _CURRENT_TIME,
    'current_date': _CURRENT_DATE,
    'files': _files_table_function,
    '||': sql_function(operator.add, [unicode, unicode, unicode]),
    '+': sql_function(operator.add, [numbers.Number, numbers.Number, numbers.Number]),
    '-': sql_function(operator.sub, [numbers.Number, numbers.Number, numbers.Number]),
    '*': sql_function(operator.mul, [numbers.Number, numbers.Number, numbers.Number]),
    '/': sql_function(operator.div, [numbers.Number, numbers.Number, numbers.Number]),
    'negate': sql_function(operator.neg, [numbers.Number, numbers.Number]),
    '>': sql_function(operator.gt, [numbers.Number, numbers.Number, numbers.Number]),
    '>=': sql_function(operator.ge, [numbers.Number, numbers.Number, numbers.Number]),
    '<': sql_function(operator.lt, [numbers.Number, numbers.Number, numbers.Number]),
    '<=': sql_function(operator.le, [numbers.Number, numbers.Number, numbers.Number]),
    '=': sql_function(operator.eq, [numbers.Number, numbers.Number, numbers.Number]),
    '<>': sql_function(operator.ne, [numbers.Number, numbers.Number, numbers.Number]),
    '^': sql_function(operator.pow, [numbers.Number, numbers.Number, numbers.Number]),
    '%': sql_function(operator.mod, [numbers.Number, numbers.Number, numbers.Number]),
    'length': sql_function(len, [Sized, int]),
})


# TODO(aershov182): add forbidden argument
def walk_with_depth(path, depth=0):
    try:
        names = os.listdir(path)
    except OSError as exc:
        return
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


class ExprError(Exception):
    pass


# TODO: Expr object should probably contain a reference to its location in the string
# TODO: ... (and the string itself)
class Expr(object):
    def get_type(self, scope):
        raise NotImplementedError


class QueryExpr(Expr):
    def __init__(self, select_expr, from_expr, where_expr, order_expr,
                 limit_expr, offset_expr):
        self.select_expr = select_expr
        self.from_expr = from_expr
        self.where_expr = where_expr
        self.order_expr = order_expr
        self.limit_expr = limit_expr
        self.offset_expr = offset_expr

    def get_value(self, context, directory):
        if directory is not None and self.from_expr is not None:
            raise ExprError("You can't specify both directory and from")
        if self.from_expr is None:
            self.from_expr = StringExpr(directory)
        if isinstance(self.from_expr, StringExpr):
            self.from_expr = FunctionExpr('files', [self.from_expr])
        if self.where_expr is None:
            self.where_expr = LiteralExpr(True)
        if self.order_expr is None:
            self.order_expr = []
        if self.offset_expr is None:
            self.offset_expr = LiteralExpr(0)
        rows = []
        from_type = self.from_expr.get_type(context)
        select_context = MergedContext(from_type, context)
        row_type = OrderedDict()
        for i, expr in enumerate(self.select_expr):
            row_type[get_name(expr, 'column_{:d}'.format(i))] = expr.get_type(select_context)
        for from_row in self.from_expr.get_value(context):
            row_context = MergedContext(
                Context(from_row),
                context
            )
            if self.where_expr.get_value(row_context):
                row = []
                for expr in self.select_expr:
                    column = expr.get_value(row_context)
                    row.append(column)
                rows.append(row)

        def key(row):
            # TODO(aershov182): `ORDER BY` context should depend on select_expr
            result = [e.get_value(MergedContext(dict(zip(row_type, row)), context))
                      for e in self.order_expr]
            return result

        rows = sorted(rows, key=key)
        rows = rows[self.offset_expr.get_value(context):]
        if self.limit_expr is not None:
            rows = rows[:self.limit_expr.get_value(context)]

        return Table(row_type, rows)


def get_name(expr, default):
    if isinstance(expr, NameExpr):
        return expr.name
    return default


class Table(object):
    def __init__(self, row_type, rows):
        self.row_type = row_type
        self.rows = rows

    def __iter__(self):
        py_type = namedtuple('SomeRow', list(self.row_type.keys()))
        for row in self.rows:
            yield py_type._make(row)


class SelectExpr(Expr):
    def __init__(self, column_exprs):
        self.column_exprs = column_exprs


class FromExpr(Expr):
    def __init__(self, from_expr):
        self.from_expr = from_expr


class LsqlTypeError(Exception):
    pass


class LsqlNameError(LsqlTypeError):
    def __init__(self, name):
        self.name = name


# TODO: do we need Lsql* prefix in class names?
class LsqlType(object):
    pass


class LsqlTableType(LsqlType):
    def __init__(self, schema):
        self.schema = schema


class LsqlFunction(object):
    pass


class LsqlString(LsqlType, unicode):
    pass


class LsqlInt(LsqlType, int):
    pass


class LsqlFloat(LsqlType, float):
    pass


# class LsqlBool(LsqlType, bool):
#     pass


class MergedContext(object):
    def __init__(self, *contexts):
        self.contexts = contexts

    def __getitem__(self, item):
        for context in self.contexts:
            try:
                return context[item]
            except KeyError:
                pass
        raise KeyError(item)

    def __repr__(self):
        return 'MergedContext({!s})'.format(
            ', '.join(map(repr, self.contexts))
        )


class NameExpr(Expr):
    def __init__(self, name):
        self.name = name

    def get_type(self, scope):
        try:
            return scope[self.name]
        except KeyError:
            raise LsqlNameError(self.name)

    def get_value(self, context):
        return context[self.name]

    def __repr__(self):
        return 'NameExpr(name={!r})'.format(self.name)


class LiteralExpr(Expr):
    def __init__(self, value):
        self.value = value

    def get_type(self, scope):
        return type(self.value)

    def get_value(self, context):
        return self.value

    def __repr__(self):
        return '{!s}(value={!r})'.format(self.__class__.__name__, self.value)


class StringExpr(LiteralExpr):
    def get_type(self, scope):
        return LsqlType


class IntExpr(LiteralExpr):
    def get_type(self, scope):
        return LsqlInt


class FloatExpr(LiteralExpr):
    def get_type(self, scope):
        return LsqlFloat


class FunctionExpr(Expr):
    def __init__(self, function_name, arg_exprs):
        self.function_name = function_name
        self.arg_exprs = arg_exprs

    def get_type(self, scope):
        function = scope[self.function_name]
        return function.return_type

    def get_value(self, context):
        function = context[self.function_name]
        args = [arg_expr.get_value(context) for arg_expr in self.arg_exprs]
        return function(*args)

    def __repr__(self):
        return 'FunctionExpr(function_name={!r}, arg_exprs={!r})'.format(
            self.function_name, self.arg_exprs
        )


class AndExpr(Expr):
    def __init__(self, left_expr, right_expr):
        self.left_expr = left_expr
        self.right_expr = right_expr

    def get_value(self, context):
        return all(arg_expr.get_value(context)
                   for arg_expr in [self.left_expr, self.right_expr])


# TODO(aershov182): DRY it up with AndExpr
class OrExpr(Expr):
    def __init__(self, left_expr, right_expr):
        self.left_expr = left_expr
        self.right_expr = right_expr

    def get_value(self, context):
        return any(arg_expr.get_value(context)
                   for arg_expr in [self.left_expr, self.right_expr])
