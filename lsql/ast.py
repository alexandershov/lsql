from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple, OrderedDict, Sized
from copy import copy
from datetime import datetime
from functools import total_ordering, wraps
from grp import getgrgid
from pwd import getpwuid
from stat import S_IXUSR
import numbers
import operator
import os

import errno

from lsql.errors import LsqlError

_MISSING = object()

ASC = 1
DESC = -1


class Namespace(object):
    """
    Namespace is an immutable case-insensitive dictionary with unicode keys.
    """

    def __init__(self, items):
        """
        :param items: dictionary unicode -> value
        """
        self._items = {self.prepare_key(key): value
                       for key, value in items.viewitems()}

    @classmethod
    def prepare_key(cls, key):
        assert isinstance(key, unicode)
        return key.lower()

    def __getitem__(self, item):
        return self._items[self.prepare_key(item)]

    def __contains__(self, item):
        return self.prepare_key(item) in self._items

    def __repr__(self):
        return '{}(items={!r})'.format(self.__class__.__name__, self._items)


class Context(Namespace):
    pass


class EmptyContext(Context):
    def __init__(self):
        pass

    def __getitem__(self, item):
        raise KeyError

    def __contains__(self, item):
        return False

    def __repr__(self):
        return 'EmptyContext()'


class MergedContext(Context):
    def __init__(self, *contexts):
        for context in contexts:
            assert isinstance(context, Context)
        self._contexts = contexts

    def __getitem__(self, item):
        for context in self._contexts:
            try:
                return context[item]
            except KeyError:
                pass
        raise KeyError(item)

    def __contains__(self, item):
        return any((item in context) for context in self._contexts)

    def __repr__(self):
        return 'MergedContext({!s})'.format(
            ', '.join(map(repr, self._contexts))
        )


class NodeVisitor(object):
    def visit(self, node):
        raise NotImplementedError


class NodeTransformer(NodeVisitor):
    def visit(self, node):
        """
        If you don't want to transform the node, then just return `node`.
        If you want to remove node, return None.
        Otherwise return another node that will replace `node` in the ast.
        Don't modify `node` in-place. Return a new node.

        :type node: Node
        :rtype: Node
        """
        raise NotImplementedError


class FileTableType(Namespace):
    @property
    def star_columns(self):
        return Stat.MAIN_ATTRS

    @property
    def default_columns(self):
        return ['name']

    def as_dict(self):
        return self._items


class FileTableContext(Context):
    def __init__(self, stat):
        """
        :type stat: lsql.ast.Stat
        """
        self._stat = stat

    def __getitem__(self, item):
        return self._stat[self.prepare_key(item)]

    def __contains__(self, item):
        return self.prepare_key(item) in self._stat.ATTRS

    def __repr__(self):
        return 'FileTableContext(stat={!r})'.format(self._stat)


class TaggedUnicode(unicode):
    def __new__(cls, string, tags, encoding='utf-8', errors='strict'):
        return super(TaggedUnicode, cls).__new__(cls, string, encoding, errors)

    def __init__(self, string, tags, encoding='utf-8', errors='strict'):
        super(TaggedUnicode, self).__init__(string, encoding, errors)
        self.tags = tags


@total_ordering
class Null(object):
    def __repr__(self):
        return 'NULL'

    def __nonzero__(self):
        """
        Null is always False in boolean context.
        """
        return False

    def __lt__(self, other):
        return True


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
        return datetime.fromtimestamp(self).isoformat()


class Mode(object):
    def __init__(self, mode):
        self.mode = mode

    def __str__(self):
        return oct(self.mode)


class Stat(object):
    ATTRS = OrderedDict.fromkeys([
        'fullpath', 'size', 'owner',
        'path', 'fulldir', 'dir', 'name', 'extension', 'ext', 'no_ext',
        'mode', 'group', 'atime', 'mtime', 'ctime', 'birthtime',
        'depth', 'type', 'device', 'hardlinks', 'inode',
        'text', 'lines', 'is_executable', 'is_exec'
    ])

    ATTR_ALIASES = {
        'ext': 'extension',
        'is_exec': 'is_executable',
    }

    MAIN_ATTRS = ['mode', 'owner', 'size', 'mtime', 'path']

    def __init__(self, path, depth):
        self._path = path
        self.depth = depth
        self.__stat = os.lstat(path)

    @property
    def path(self):
        return TaggedUnicode(self._path, self.get_tags())

    @property
    def fullpath(self):
        return TaggedUnicode(
            os.path.normpath(os.path.join(os.getcwd(), self._path)),
            self.get_tags(),
        )

    @property
    def size(self):
        if self.type == 'dir':
            return get_dir_size(self._path)
        return self.__stat.st_size

    @property
    def owner(self):
        return getpwuid(self.__stat.st_uid).pw_name

    @property
    def fulldir(self):
        return os.path.dirname(self.fullpath)

    @property
    def dir(self):
        return os.path.dirname(self._path)

    @property
    def _name(self):
        return os.path.basename(self._path)

    @property
    def name(self):
        return TaggedUnicode(self._name, self.get_tags())

    @property
    def extension(self):
        extension = os.path.splitext(self._path)[1]
        return extension[1:]  # skip dot

    @property
    def no_ext(self):
        return TaggedUnicode(os.path.splitext(self._name)[0], self.get_tags())

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
        if os.path.islink(self._path):
            return 'link'
        elif os.path.isdir(self._path):
            return 'dir'
        elif os.path.isfile(self._path):
            return 'file'
        elif os.path.ismount(self._path):
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
        with open(self._path, 'rb') as fileobj:
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
        return FileTableType({
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

    def get_context(self):
        return FileTableContext(self)


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


def agg_function(function, signature):
    @wraps(function)
    def wrapper(*args):
        return function(*args)

    wrapper.return_type = signature[-1]
    return wrapper


def count_agg(items):
    result = 0
    for item in items:
        if item is not NULL:
            result += 1
    return result


def sum_agg(items):
    result = 0
    for item in items:
        if item is not NULL:
            result += item
    return result


def min_agg(items):
    result = NULL
    for item in items:
        if result is NULL:
            result = item
        elif item is not NULL and item < result:
            result = item
    return result


def max_agg(items):
    result = NULL
    for item in items:
        if item is not NULL and item > result:
            result = item
    return result


def avg_agg(items):
    total = 0
    count = 0
    for item in items:
        if item is not NULL:
            total += item
            count += 1
    return total / count


class AnyIterable(object):
    pass


class NumberIterable(object):
    pass


TYPES = {
    numbers.Number, bool, unicode, int,
    AnyIterable, NumberIterable,
}

AGG_FUNCTIONS = Context({
    'count': agg_function(count_agg, [AnyIterable, int]),
    'sum': agg_function(sum_agg, [NumberIterable, int]),
    'max': agg_function(max_agg, [NumberIterable, object]),
    'min': agg_function(min_agg, [NumberIterable, numbers.Number]),
    'avg': agg_function(avg_agg, [NumberIterable, numbers.Number]),
})

# TODO(aershov182): probably we don't need to prefix private names with underscore
BASE_CONTEXT = Context({
    'null': NULL,
    'current_time': _CURRENT_TIME,
    'current_date': _CURRENT_DATE,
})


def in_(x, y):
    return x in y


FUNCTIONS = Context({
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
    'in': sql_function(in_, [object, AnyIterable])
})

BUILTIN_CONTEXT = MergedContext(AGG_FUNCTIONS, BASE_CONTEXT)


# TODO(aershov182): add forbidden argument and handle case with permissions gracefully
def walk_with_depth(path, depth=0):
    try:
        names = os.listdir(path)
    except OSError as exc:
        # TODO(aershov182): ENOENT or EEXISTS?
        if exc.errno == errno.ENOENT:
            raise DirectoryDoesNotExistError(path)
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


class ExprError(LsqlError):
    pass


class DirectoryDoesNotExistError(ExprError):
    def __init__(self, path):
        self.path = path


# TODO: Node object should contain a reference to its location in the string (and the string itself)
class Node(object):
    def __init__(self, children=None, parent=None):
        # we make a tuple out of children, because we want it to be hashable
        if children is None:
            children = ()
        self.children = tuple(child.replace(parent=self) for child in children)
        self.parent = parent

    def get_type(self, scope):
        raise NotImplementedError

    def walk(self, visitor):
        visitor.visit(self)
        for child in self.children:
            child.walk(visitor)

    def transform(self, transformer):
        result = transformer.visit(self)
        transformed_children = [child.transform(transformer) for child in self.children]
        return result.replace(children=transformed_children)

    def replace(self, children=_MISSING, parent=_MISSING):
        result = copy(self)  # TODO: maybe implement __copy__ method?
        if children is not _MISSING:
            result.children = children
        if parent is not _MISSING:
            result.parent = parent
        return result

    def get_value(self, context):
        raise NotImplementedError

    def check_type(self, scope):
        for child in self.children:
            child.check_type(scope)

    def __iter__(self):
        return iter(self.children)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.children == other.children

    def __hash__(self):
        return hash(self.children)

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        # we can't show parent because of infinite recursion
        return '{}(children={!r})'.format(self.__class__.__name__, self.children)


class NullNode(Node):
    def __eq__(self, other):
        return isinstance(other, NullNode)

    def __copy__(self):
        return NullNode()


class OrderByPartNode(Node):
    def __init__(self, expr, direction):
        self.expr = expr
        self.direction = direction
        super(OrderByPartNode, self).__init__(children=[expr])

    def get_value(self, context):
        return self.expr.get_value(context)

    def get_type(self, scope):
        return self.expr.get_type(scope)

    def __eq__(self, other):
        return super(OrderByPartNode, self).__eq__(other) and (self.direction == other.direction)

    def __hash__(self):
        return hash((self.children, self.direction))


@total_ordering
class OrderByKey(object):
    def __init__(self, row, exprs):
        assert len(row) == len(list(exprs))
        self.row = row
        self.exprs = exprs

    def __lt__(self, other):
        assert len(self.row) == len(other.row)
        for expr, x, y in zip(self.exprs, self.row, other.row):
            if expr.direction == ASC:
                op = operator.lt
            else:
                op = operator.gt
            if op(x, y):
                return True
        return False

    def __eq__(self, other):
        return self.row == other.row


class BetweenNode(Node):
    def __init__(self, value_expr, first_expr, last_expr):
        self.value_expr = value_expr
        self.first_expr = first_expr
        self.last_expr = last_expr
        super(BetweenNode, self).__init__(children=[self.value_expr, self.first_expr, self.last_expr])

    def get_type(self, scope):
        return bool

    def get_value(self, context):
        return self.first_expr.get_value(context) <= self.value_expr.get_value(context) <= self.last_expr.get_value(
            context)


class QueryNode(Node):
    def __init__(self, select_expr, from_expr, where_expr, order_expr,
                 limit_expr, offset_expr):
        self.select_expr = select_expr
        self.from_expr = from_expr
        self.where_expr = where_expr
        self.order_expr = order_expr
        self.limit_expr = limit_expr
        self.offset_expr = offset_expr
        if self.from_expr is None:
            self.from_expr = NameNode('cwd')
        if isinstance(self.from_expr, (NameNode, ValueNode)):
            self.from_expr = FunctionNode('files', [self.from_expr])
        from_type = self.from_expr.get_type(BUILTIN_CONTEXT)
        if isinstance(self.select_expr, SelectStarExpr):
            if hasattr(from_type, 'star_columns'):
                self.select_expr = SelectNode(
                    [
                        NameNode(column) for column in from_type.star_columns
                        ])
            else:
                self.select_expr = SelectNode(
                    [
                        NameNode(column) for column in from_type
                        ])
        if self.select_expr is None:
            self.select_expr = SelectNode(list(map(NameNode, from_type.default_columns)))
        if self.where_expr is None:
            self.where_expr = ValueNode(True)
        if self.order_expr is None:
            self.order_expr = OrderNode([])
        if self.limit_expr is None:
            self.limit_expr = ValueNode(float('inf'))
        if self.offset_expr is None:
            self.offset_expr = ValueNode(0)
        super(QueryNode, self).__init__(children=[
            self.select_expr, self.from_expr, self.where_expr, self.order_expr, self.limit_expr,
            self.offset_expr,
        ])

    def get_value(self, context):
        rows = []
        from_type = self.from_expr.get_type(context)
        select_context = MergedContext(Context(from_type.as_dict()), context)
        row_type = OrderedDict()
        for i, expr in enumerate(self.select_expr):
            row_type[get_name(expr, 'column_{:d}'.format(i))] = expr.get_type(select_context)

        def key(row):
            # TODO(aershov182): `ORDER BY` context should depend on select_expr
            result = [e.get_value(MergedContext(row.get_context(), context))
                      for e in self.order_expr]
            return OrderByKey(result, self.order_expr)

        filtered_rows = []

        keys = []
        for from_row in self.from_expr.get_value(context):
            row_context = MergedContext(
                from_row.get_context(),
                context
            )
            keys.append(key(from_row))
            if self.where_expr.get_value(row_context):
                filtered_rows.append(from_row)
        for row in filtered_rows:
            row_context = MergedContext(
                row.get_context(),
                context
            )
            cur_row = []
            for expr in self.select_expr:
                column = expr.get_value(row_context)
                cur_row.append(column)
            rows.append(cur_row)

        rows = [row for _, row in sorted(zip(keys, rows))]
        rows = rows[self.offset_expr.get_value(context):]
        value = self.limit_expr.get_value(context)
        if value != float('inf'):
            rows = rows[:value]
        return Table(row_type, rows)


def get_name(expr, default):
    if isinstance(expr, NameNode):
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


class SelectNode(Node):
    pass


class OrderNode(Node):
    pass


class FromNode(Node):
    def __init__(self, from_expr):
        self.from_expr = from_expr
        super(FromNode, self).__init__(children=[self.from_expr])


class GroupNode(Node):
    # TODO: don't allow having_expr equal to None
    def __init__(self, group_exprs, having_expr=None):
        if having_expr is None:
            having_expr = ValueNode(True)
        self.group = group_exprs
        self.having_expr = having_expr
        super(GroupNode, self).__init__(children=(group_exprs + [self.having_expr]))

    def check_type(self, scope):
        super(GroupNode, self).check_type(scope)
        self.having_expr.check_type(scope)


class NameNode(Node):
    def __init__(self, name):
        self.name = name
        super(NameNode, self).__init__()

    def get_type(self, scope):
        return scope[self.name]

    def get_value(self, context):
        return context[self.name]

    def __eq__(self, other):
        return super(NameNode, self).__eq__(other) and self.name == other.name

    def __repr__(self):
        return 'NameNode(name={!r})'.format(self.name)


class SelectStarExpr(SelectNode):
    def __init__(self):
        super(SelectStarExpr, self).__init__()


class ValueNode(Node):
    def __init__(self, value):
        self.value = value
        super(ValueNode, self).__init__()

    def get_type(self, scope):
        return type(self.value)

    def get_value(self, context):
        return self.value

    def __repr__(self):
        return '{!s}(value={!r})'.format(self.__class__.__name__, self.value)

    def __eq__(self, other):
        return super(ValueNode, self).__eq__(other) and self.value == other.value


class ArrayNode(Node):
    def __init__(self, exprs):
        self.exprs = exprs
        super(ArrayNode, self).__init__(children=self.exprs)

    def get_type(self, scope):
        return AnyIterable

    def get_value(self, context):
        return [e.get_value(context) for e in self.exprs]

    def __repr__(self):
        return '{!s}(exprs={!r})'.format(self.__class__.__name__, self.exprs)


class FunctionNode(Node):
    def __init__(self, function_name, arg_exprs):
        self.function_name = function_name
        self.arg_exprs = arg_exprs
        super(FunctionNode, self).__init__(children=arg_exprs)

    @property
    def function(self):
        return FUNCTIONS[self.function_name]

    def get_type(self, scope):
        return self.function.return_type

    def get_value(self, context):
        args = [arg_expr.get_value(context) for arg_expr in self.arg_exprs]
        return self.function(*args)

    def __eq__(self, other):
        return super(FunctionNode, self).__eq__(other) and (self.function_name == other.function_name)

    def __hash__(self, other):
        return hash((self.children, self.function_name))

    def __repr__(self):
        return 'FunctionNode(function_name={!r}, arg_exprs={!r})'.format(
            self.function_name, self.arg_exprs
        )


class AndNode(Node):
    def __init__(self, left_expr, right_expr):
        self.left_expr = left_expr
        self.right_expr = right_expr
        super(AndNode, self).__init__(children=[self.left_expr, self.right_expr])

    def get_value(self, context):
        return all(arg_expr.get_value(context)
                   for arg_expr in [self.left_expr, self.right_expr])


# TODO(aershov182): DRY it up with AndNode
class OrNode(Node):
    def __init__(self, left_expr, right_expr):
        self.left_expr = left_expr
        self.right_expr = right_expr
        super(OrNode, self).__init__(children=[left_expr, right_expr])

    def get_value(self, context):
        return any(arg_expr.get_value(context)
                   for arg_expr in [self.left_expr, self.right_expr])
