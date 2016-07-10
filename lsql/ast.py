from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict, namedtuple, OrderedDict, Sized
from datetime import datetime
from functools import total_ordering, wraps
from grp import getgrgid
from itertools import chain
from pwd import getpwuid
from stat import S_IXUSR
import errno
import numbers
import operator
import os

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

    def __getitem__(self, key):
        return self._items[self.prepare_key(key)]

    def __contains__(self, key):
        return self.prepare_key(key) in self._items

    def __repr__(self):
        return '{}(items={!r})'.format(self.__class__.__name__, self._items)

    @classmethod
    def prepare_key(cls, key):
        assert isinstance(key, unicode)
        return key.lower()


class Context(Namespace):
    pass


class EmptyContext(Context):
    def __init__(self):
        pass

    def __getitem__(self, key):
        raise KeyError

    def __contains__(self, key):
        return False

    def __repr__(self):
        return 'EmptyContext()'


class CombinedContext(Context):
    def __init__(self, *contexts):
        for context in contexts:
            assert isinstance(context, Context)
        self._contexts = contexts

    def __getitem__(self, key):
        for context in self._contexts:
            try:
                return context[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def __repr__(self):
        return 'CombinedContext(contexts={!r})'.format(self._contexts)


# TODO: think about better Expr & Visitor representation
class NodeVisitor(object):
    def visit(self, node):
        raise NotImplementedError


class AggFunctionsVisitor(NodeVisitor):
    def __init__(self):
        self.agg_function_nodes = []

    def visit(self, node):
        if isinstance(node, FunctionNode):
            if node.function_name in AGGREGATES:
                self.agg_function_nodes.append(node)

    @property
    def has_agg_functions(self):
        return bool(self.agg_function_nodes)


class TypeNodeVisitor(NodeVisitor):
    def __init__(self, node_class):
        self.node_class = node_class
        self.nodes = []

    def visit(self, node):
        if isinstance(node, self.node_class):
            self.nodes.append(node)


def has_agg_functions_nodes(node):
    return bool(get_agg_function_nodes(node))


# TODO: use get_nodes_of_type, but accurately, because in has_agg_function_nodes we don't search
# TODO: ... class, we check AGGREGATES
def get_agg_function_nodes(node):
    visitor = AggFunctionsVisitor()
    node.walk(visitor)
    return visitor.agg_function_nodes


def get_nodes_of_type(node, node_class):
    visitor = TypeNodeVisitor(node_class)
    node.walk(visitor)
    return visitor.nodes


def has_ancestor_of_type(node, ancestor_node_class):
    while node.parent is not None:
        if isinstance(node.parent, ancestor_node_class):
            return True
        node = node.parent
    return False


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


class AggFunctionsTransformer(NodeTransformer):
    # TODO: refactor it. Maybe move logic to Node.transform?
    def visit(self, node):
        if isinstance(node, FunctionNode):
            if node.function_name in AGGREGATES:
                return AggFunctionNode.create(
                    function_name=node.function_name, arg_nodes=node.children, location=node.location)
        return node


class FilesTableType(Namespace):
    @property
    def star_columns(self):
        return Stat.MAIN_ATTRS

    @property
    def default_columns(self):
        return ['name']

    def as_dict(self):
        return self._items


class FilesTableContext(Context):
    def __init__(self, stat):
        """
        :type stat: lsql.ast.Stat
        """
        self._stat = stat

    def __getitem__(self, key):
        return self._stat[self.prepare_key(key)]

    def __contains__(self, key):
        return self.prepare_key(key) in self._stat.ATTRS

    def __repr__(self):
        return 'FilesTableContext(stat={!r})'.format(self._stat)


class TaggedStr(str):
    def __new__(cls, string, tags):
        return super(TaggedStr, cls).__new__(cls, string)

    def __init__(self, string, tags):
        super(TaggedStr, self).__init__(string)
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
        """
        Null is always less than anything
        """
        return True

    def __eq__(self, other):
        return self is other  # Null is a singleton, and NULL its single instance


NULL = Null()


def get_base_context():
    current_time = datetime.utcnow()
    current_date = current_time.date()
    return Context({
        'null': NULL,
        'current_time': current_time,
        'current_date': current_date,
    })


_CURRENT_TIME = datetime.utcnow()
_CURRENT_DATE = _CURRENT_TIME.date()


def get_dir_size(path):
    size = 0
    walker = DirectoryWalker(path)
    for path, _ in walker.walk():
        if os.path.isfile(path):
            size += os.lstat(path).st_size
    return size


class Timestamp(int):
    def __str__(self):
        # TODO: not utc?
        return datetime.fromtimestamp(self).isoformat()


class Mode(object):
    def __init__(self, mode):
        self.mode = mode

    # TODO: better __str__
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
        return TaggedStr(self._path, self.get_tags())

    @property
    def fullpath(self):
        return TaggedStr(
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
        return TaggedStr(self._name, self.get_tags())

    @property
    def extension(self):
        extension = os.path.splitext(self._path)[1]
        return extension[1:]  # skip dot

    @property
    def no_ext(self):
        return TaggedStr(os.path.splitext(self._name)[0], self.get_tags())

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
            raise LsqlEvalError('birthtime is not supported on your platform')
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
        return FilesTableType({
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
        return FilesTableContext(self)


def _files_table_function(directory):
    walker = DirectoryWalker(directory)
    for path, depth in walker.walk():
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


class AnyIterable(object):
    pass


class NumberIterable(object):
    pass


TYPES = {
    numbers.Number, bool, unicode, int,
    AnyIterable, NumberIterable,
}


class Aggregate(object):
    type = None  # redefine me in subclasses
    return_type = None  # redefine me in subclasses

    # TODO: call clear() from __init__ not the other way around
    def clear(self):
        self.__init__()

    def add(self, *args, **kwargs):
        raise NotImplementedError

    @property
    def value(self):
        raise NotImplementedError


class CountAggregate(Aggregate):
    type = (object, int)
    return_type = int  # TODO: DRY return_type and type

    def __init__(self):
        self._count = 0

    def add(self, value):
        if value is not NULL:
            self._count += 1

    @property
    def value(self):
        return self._count


class SumAggregate(Aggregate):
    type = (object, numbers.Number)
    return_type = numbers.Number  # TODO: DRY return_type and type

    def __init__(self):
        self._sum = 0

    def add(self, value):
        if value is not NULL:
            self._sum += value

    @property
    def value(self):
        return self._sum


class MaxAggregate(Aggregate):
    type = (object, object)
    return_type = object  # TODO: DRY return_type and type

    def __init__(self):
        self._max = NULL

    def add(self, value):
        if value is not NULL:
            if self._max is NULL:
                self._max = value
            else:
                self._max = max(self._max, value)

    @property
    def value(self):
        return self._max


# TODO: DRY all aggregates
class MinAggregate(Aggregate):
    type = (object, object)
    return_type = object  # TODO: DRY return_type and type

    def __init__(self):
        self._min = NULL

    def add(self, value):
        if value is not NULL:
            if self._min is NULL:
                self._min = value
            else:
                self._min = min(self._min, value)

    @property
    def value(self):
        return self._min


class AvgAggregate(Aggregate):
    type = (numbers.Number, float)
    return_type = float  # TODO: DRY return_type and type

    def __init__(self):
        self._sum = 0
        self._count = 0

    def add(self, value):
        if value is not NULL:
            self._sum += value
            self._count += 1

    @property
    def value(self):
        # TODO: fix this check
        if self._count == 0:
            return NULL
        return self._sum / self._count


AGGREGATES = {
    'count': CountAggregate,
    'sum': SumAggregate,
    'max': MaxAggregate,
    'min': MinAggregate,
    'avg': AvgAggregate,
}

BASE_CONTEXT = get_base_context()


def in_(x, y):
    return x in y


# TODO(aershov182): probably we don't need to prefix private names with underscore
# TODO: builtin-function don't belong into context, there should be separate namespace for functions
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

BUILTIN_CONTEXT = BASE_CONTEXT


class DirectoryWalker(object):
    def __init__(self, path):
        self.path = path
        self.forbidden_paths = []

    def walk(self, path=None, depth=0):
        if path is None:
            path = self.path
        try:
            names = os.listdir(path)
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                raise DirectoryDoesNotExistError(path)
            elif exc.errno == errno.EPERM:
                self.forbidden_paths.append(path)
            else:
                raise
        dirs = []
        for name in names:
            full_path = os.path.join(path, name)
            if os.path.isdir(full_path):
                dirs.append(full_path)
            yield full_path, depth
        for d in dirs:
            if not os.path.islink(d):
                for x in self.walk(d, depth + 1):
                    yield x


class LsqlEvalError(LsqlError):
    pass


class IllegalGroupBy(LsqlEvalError):
    # TODO: add message to constructor
    def __init__(self, node):
        self.node = node


class DirectoryDoesNotExistError(LsqlEvalError):
    def __init__(self, path):
        self.path = path


Location = namedtuple('Location', ['text', 'start', 'end'])


# TODO: Node object should contain a reference to its location in the string (and the string itself)
# TODO: think about a good solution to e.g dualism of children and some other properties (e.g FunctionNode.arg_exprs)
class Node(namedtuple('Node', ['data', 'children', 'location', 'parent'])):
    def __new__(cls, data=None, children=None, location=None, parent=None):
        if children is None:
            children = []
        return super(Node, cls).__new__(cls, data=data, children=children, location=location, parent=parent)

    @classmethod
    def create(cls, children=None, location=None, parent=None):
        # no data by default
        return cls(children=children, location=location, parent=parent)

    def get_type(self, scope):
        raise NotImplementedError

    def walk(self, visitor):
        for child in self.children:
            child = child._replace(parent=self)
            child.walk(visitor)
        visitor.visit(self)

    def transform(self, transformer):
        transformed_children = [child.transform(transformer) for child in self.children]
        return transformer.visit(self)._replace(children=transformed_children)

    def get_value(self, context):
        raise NotImplementedError

    def check_type(self, scope):
        for child in self.children:
            child.check_type(scope)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        # we ignore location and parent, because they don't matter in equality
        return self.data == other.data and self.children == other.children

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        # we can't show parent because of infinite recursion
        return '{}(data={!r}, children={!r}, location={!r})'.format(
            self.__class__.__name__, self.data, self.children, self.location)


class NullNode(Node):
    @classmethod
    def create(cls, parent=None, children=None, location=None):
        return cls(data=None, children=children, location=location, parent=parent)

    def __eq__(self, other):
        return isinstance(other, NullNode)


class OrderByPartNode(Node):
    @classmethod
    def create(cls, node, direction, location=None, parent=None):
        return cls(data=direction, children=[node], location=location, parent=parent)

    @property
    def direction(self):
        return self.data

    @property
    def node(self):
        return self.children[0]

    def get_value(self, context):
        return self.node.get_value(context)

    def get_type(self, scope):
        return self.node.get_type(scope)

    def __hash__(self):
        return hash((self.children, self.direction))


@total_ordering
class OrderByKey(object):
    def __init__(self, row, nodes):
        assert len(row) == len(list(nodes))
        self.row = row
        self.nodes = nodes

    def __lt__(self, other):
        assert len(self.row) == len(other.row)
        for node, x, y in zip(self.nodes, self.row, other.row):
            if node.direction == ASC:
                op = operator.lt
            else:
                op = operator.gt
            if x == y:
                continue
            elif op(x, y):
                return True
            else:
                return False
        return False

    def __eq__(self, other):
        return self.row == other.row


# TODO: use namedtuple for children (and in other *Node classes too)
class BetweenNode(Node):
    @classmethod
    def create(cls, value_node, first_node, last_node, location=None, parent=None):
        return cls(children=[value_node, first_node, last_node], location=location,
                   parent=parent)

    @property
    def value_node(self):
        return self.children[0]

    @property
    def first_node(self):
        return self.children[1]

    @property
    def last_node(self):
        return self.children[2]

    def get_type(self, scope):
        return bool

    def get_value(self, context):
        return self.first_node.get_value(context) <= self.value_node.get_value(context) <= self.last_node.get_value(
            context)


class QueryNode(Node):
    # TODO: add slots to every Node subclass
    __slots__ = ()

    @classmethod
    def create(cls, select_node, from_node, where_node, group_node, having_node, order_node,
               limit_node, offset_node, location=None, parent=None):
        if from_node is None:
            from_node = NameNode.create('cwd')
        if isinstance(from_node, (NameNode, ValueNode)):
            from_node = FunctionNode.create('files', [from_node], location=from_node.location)
        from_type = from_node.get_type(BUILTIN_CONTEXT)
        if isinstance(select_node, SelectStarNode):
            if hasattr(from_type, 'star_columns'):
                select_node = SelectNode.create(
                    [
                        NameNode.create(column) for column in from_type.star_columns
                        ],
                )
            else:
                select_node = SelectNode.create(
                    [
                        NameNode.create(column) for column in from_type
                        ])
        if select_node is None:
            select_node = SelectNode.create(list(map(NameNode.create, from_type.default_columns)))
        if where_node is None:
            where_node = ValueNode.create(True)
        if order_node is None:
            order_node = OrderNode.create()
        if limit_node is None:
            limit_node = ValueNode.create(float('inf'))
        if offset_node is None:
            offset_node = ValueNode.create(0)

        if has_agg_functions_nodes(where_node):
            raise LsqlEvalError('aggregate functions are not allowed in WHERE')
        if group_node is None:
            if any(has_agg_functions_nodes(node) for node in chain(select_node.children, order_node.children)):
                group_node = GroupNode.create()
            elif having_node is None:
                group_node = FakeGroupNode.create()
            else:
                group_node = GroupNode.create()
        if having_node is None:
            having_node = ValueNode.create(True)
        if has_agg_functions_nodes(group_node):
            raise IllegalGroupBy('aggregate functions are not allowed in GROUP BY')
        transformer = AggFunctionsTransformer()
        select_node = select_node.transform(transformer)
        having_node = having_node.transform(transformer)
        order_node = order_node.transform(transformer)
        return cls(
            children=[select_node, from_node, where_node, group_node, having_node, order_node,
                      limit_node, offset_node],
            location=location,
            parent=parent,
        )

    @property
    def select_node(self):
        return self.children[0]

    @property
    def from_node(self):
        return self.children[1]

    @property
    def where_node(self):
        return self.children[2]

    @property
    def group_node(self):
        return self.children[3]

    @property
    def having_node(self):
        return self.children[4]

    @property
    def order_node(self):
        return self.children[5]

    @property
    def limit_node(self):
        return self.children[6]

    @property
    def offset_node(self):
        return self.children[7]

    def get_value(self, context):
        rows = []
        from_type = self.from_node.get_type(context)
        if not isinstance(self.group_node, FakeGroupNode):
            name_nodes = []
            agg_nodes = []
            for node in [self.select_node, self.having_node, self.order_node]:
                name_nodes.extend(get_nodes_of_type(node, NameNode))
                agg_nodes.extend(get_nodes_of_type(node, AggFunctionNode))
            for name_node in name_nodes:
                if (
                    name_node not in self.group_node.children) and name_node.name in from_type and not has_ancestor_of_type(
                    name_node, AggFunctionNode):
                    if all((node not in self.group_node.children) for node in up_to_root(name_node)):
                        raise IllegalGroupBy(name_node)
            for agg_node in agg_nodes:
                if has_ancestor_of_type(agg_node, AggFunctionNode):
                    # TODO: add message
                    raise IllegalGroupBy(agg_node)
        select_context = CombinedContext(Context(from_type.as_dict()), context)
        row_type = OrderedDict()
        for i, node in enumerate(self.select_node.children):
            # TODO: check it in regard to group by
            row_type[get_name(node, 'column_{:d}'.format(i))] = node.get_type(select_context)

        def key(row):
            # TODO(aershov182): `ORDER BY` context should depend on select_node
            result = [e.get_value(CombinedContext(row.get_context(), context))
                      for e in self.order_node.children]
            return OrderByKey(result, self.order_node.children)

        filtered_rows = []

        keys = []
        for from_row in self.from_node.get_value(context):
            row_context = CombinedContext(
                from_row.get_context(),
                context
            )
            if self.where_node.get_value(row_context):
                keys.append(key(from_row))
                filtered_rows.append(from_row)

        if not isinstance(self.group_node, FakeGroupNode):
            keys = []
            agg_function_nodes = get_agg_function_nodes(self)
            grouped = defaultdict(list)  # group_key -> rows
            # TODO: check that stuff in select_expr and having_expr are legal
            for row in filtered_rows:
                row_context = CombinedContext(
                    row.get_context(),
                    context
                )
                key = tuple(node.get_value(row_context) for node in self.group_node.children)
                grouped[key].append(row)

            for key, grouped_rows in grouped.viewitems():
                for agg_node in agg_function_nodes:
                    agg_node.clear_aggregate()
                cur_row = [None] * len(self.select_node.children)
                order_row = [None] * len(self.order_node.children)
                cond = False
                for row in grouped_rows:
                    row_context = CombinedContext(
                        row.get_context(),
                        context
                    )
                    for i, node in enumerate(self.select_node.children):
                        if node in self.group_node:
                            idx = self.group_node.children.index(node)
                            column = key[idx]
                        else:
                            column = node.get_value(row_context)
                        cur_row[i] = column
                    for i, node in enumerate(self.order_node.children):
                        if node.node in self.group_node.children:
                            idx = self.group_node.children.index(node.node)
                            column = key[idx]
                        else:
                            column = node.get_value(row_context)
                        order_row[i] = column
                    cond = self.having_node.get_value(row_context)
                if cond:
                    rows.append(cur_row)
                    keys.append(OrderByKey(order_row, self.order_node.children))
        else:
            for row in filtered_rows:
                row_context = CombinedContext(
                    row.get_context(),
                    context
                )
                cur_row = []
                for node in self.select_node.children:
                    column = node.get_value(row_context)
                    cur_row.append(column)
                rows.append(cur_row)

        rows = [row for _, row in sorted(zip(keys, rows))]
        rows = rows[self.offset_node.get_value(context):]
        value = self.limit_node.get_value(context)
        if value != float('inf'):
            rows = rows[:value]
        return Table(row_type, rows)


def get_name(node, default):
    if isinstance(node, NameNode):
        return node.name
    return default


def up_to_root(node):
    while node is not None:
        yield node
        node = node.parent


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
    @classmethod
    def create(cls, from_node, location=None, parent=None):
        return cls(children=[from_node], location=location, parent=parent)

    @property
    def from_node(self):
        return self.children[0]


class GroupNode(Node):
    @property
    def groups(self):
        return self.children


class FakeGroupNode(Node):
    pass


# TODO: do we need this class
class HavingNode(Node):
    @classmethod
    def create(cls, condition, location=None, parent=None):
        return cls(children=[condition], location=location, parent=None)

    @property
    def condition(self):
        return self.children[0]


class NameNode(Node):
    @classmethod
    def create(cls, name, location=None, parent=None):
        return cls(data=name, location=location, parent=parent)

    @property
    def name(self):
        return self.data

    def get_type(self, scope):
        return scope[self.name]

    def get_value(self, context):
        return context[self.name]

    def __repr__(self):
        return 'NameNode(name={!r})'.format(self.name)


class SelectStarNode(SelectNode):
    @classmethod
    def create(cls, location=None, parent=None):
        return cls(location=location, parent=parent)


class ValueNode(Node):
    @classmethod
    def create(cls, value, location=None, parent=None):
        return cls(data=value, location=None, parent=None)

    @property
    def value(self):
        return self.data

    def get_type(self, scope):
        return type(self.value)

    def get_value(self, context):
        return self.value

    def __repr__(self):
        return '{!s}(value={!r})'.format(self.__class__.__name__, self.value)


class ArrayNode(Node):
    @classmethod
    def create(cls, nodes, location=None, parent=None):
        return cls(children=nodes, location=location, parent=parent)

    @property
    def nodes(self):
        return self.children

    def get_type(self, scope):
        return AnyIterable

    def get_value(self, context):
        return [e.get_value(context) for e in self.nodes]


class FunctionNode(Node):
    @classmethod
    def create(cls, function_name, arg_nodes, location=None, parent=None):
        return cls(data=function_name, children=arg_nodes, location=location,
                   parent=parent)

    @property
    def function_name(self):
        return self.data

    @property
    def arg_nodes(self):
        return self.children

    @property
    def function(self):
        return FUNCTIONS[self.function_name]

    def get_type(self, scope):
        return self.function.return_type

    def get_value(self, context):
        args = [arg_node.get_value(context) for arg_node in self.arg_nodes]
        return self.function(*args)

    def __repr__(self):
        return '{}(function_name={!r}, arg_nodes={!r})'.format(
            self.__class__.__name__, self.function_name, self.arg_nodes
        )


AggFunctionData = namedtuple('AggFunctionData', ['function_name', 'aggregate'])


class AggFunctionNode(FunctionNode):
    @classmethod
    def create(cls, function_name, arg_nodes, location=None, parent=None):
        aggregate = AGGREGATES[function_name]()
        data = AggFunctionData(function_name=function_name, aggregate=aggregate)
        return cls(data=data, children=arg_nodes, location=location, parent=parent)

    @property
    def function_name(self):
        return self.data.function_name

    @property
    def aggregate(self):
        return self.data.aggregate

    @property
    def function(self):
        return self.aggregate

    def clear_aggregate(self):
        self.aggregate.clear()

    def get_value(self, context):
        args = [arg_node.get_value(context) for arg_node in self.arg_nodes]
        self.aggregate.add(*args)
        return self.aggregate.value


class AndNode(Node):
    def __new__(cls, *args, **kwargs):
        return super(AndNode, cls).__new__(cls, *args, **kwargs)

    @classmethod
    def create(cls, left_node, right_node, location=None, parent=None):
        return cls(children=[left_node, right_node], location=location, parent=None)

    @property
    def left_node(self):
        return self.children[0]

    @property
    def right_node(self):
        return self.children[1]

    def get_value(self, context):
        return all(arg_node.get_value(context)
                   for arg_node in [self.left_node, self.right_node])


# TODO(aershov182): make a common class BinaryNode that'll be heir of AndNode and orNode
class OrNode(AndNode):
    def get_value(self, context):
        return any(arg_node.get_value(context)
                   for arg_node in [self.left_node, self.right_node])
