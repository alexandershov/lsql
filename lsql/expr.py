from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple, OrderedDict

# TODO: Expr object should probably contain a reference to its location in the string
# TODO: ... (and the string itself)
class Expr(object):
    def get_type(self, scope):
        raise NotImplementedError


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


class LsqlBool(LsqlType, bool):
    pass


class MergedScope(object):
    def __init__(self, *scopes):
        self.scopes = scopes

    def __getitem__(self, item):
        for scope in self.scopes:
            try:
                return scope[item]
            except KeyError:
                pass
        raise KeyError(item)


class SelectExpr(Expr):
    # TODO: add group by, offset
    def __init__(self, column_exprs, from_expr, where_expr, limit_expr):
        self.column_exprs = column_exprs
        self.from_expr = from_expr
        self.where_expr = where_expr
        self.limit_expr = limit_expr

    def get_type(self, scope):
        # scope is globals
        table_type = self.from_expr.get_type()
        if not isinstance(table_type, LsqlTableType):
            raise LsqlTypeError("{!s} doesn't return a table".format(self.from_expr))
        schema = OrderedDict()
        new_scope = MergedScope(table_type.schema, scope)
        for column_expr in self.column_exprs:
            # TODO: handle 'SELECT name AS other_name
            if isinstance(column_expr, NameExpr):
                schema[column_expr.name] = column_expr.get_type(new_scope)
            else:
                schema[str(column_expr)] = column_expr.get_type(new_scope)
        self.where_expr.get_type()  # check type
        if self.limit_expr.get_type(scope) != LsqlInt:
            raise LsqlTypeError('{!s} is not a integer'.format(self.limit_expr))
        return LsqlTableType(schema)


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


class LiteralExpr(Expr):
    def __init__(self, value):
        self.value = value

    def get_type(self, scope):
        raise NotImplementedError

    def get_value(self, context):
        return self.value


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
        if function.signature.args_count != len(self.arg_exprs):
            raise LsqlTypeError(
                'function {!s} takes {:d} arguments '
                'but given {:d} arguments', function, function.signature.args_count, len(self.arg_exprs)
            )
        for i, (expected_type, expr) in enumerate(zip(function.signature.arg_types, self.arg_exprs)):
            actual_type = expr.get_type(scope)
            if actual_type != expected_type:
                raise LsqlTypeError(
                    'arg #{:d} of function {!s} should be {!s}, '
                    'got {!s} instead', i, function, expected_type, actual_type
                )
        return function.signature.return_type

    def get_value(self, context):
        function = context[self.function_name]
        args = [arg_expr.get_value(context) for arg_expr in self.arg_exprs]
        return function(*args)


class AndExpr(FunctionExpr):
    def __init__(self, arg_exprs):
        super(AndExpr, self).__init__('and', arg_exprs)

    def get_value(self, context):
        return all(arg_expr.get_value(context) for arg_expr in self.arg_exprs)


class OrExpr(FunctionExpr):
    def __init__(self, arg_exprs):
        super(OrExpr, self).__init__('or', arg_exprs)

    def get_value(self, context):
        return any(arg_expr.get_value(context) for arg_expr in self.arg_exprs)
