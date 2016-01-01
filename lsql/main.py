import argparse

from lsql.expr import BUILTIN_SCOPE
from lsql.lexer import tokenize
from lsql.parser import parse


def main():
    parser = argparse.ArgumentParser(
        description='SQL over filesystem',
    )
    parser.add_argument('query_string', metavar='query')
    parser.add_argument(
        'directory',
        help='query working directory',
        nargs='?',
    )
    args = parser.parse_args()
    table = _run_query(args.query_string, args.directory)
    _show_table(table)


def _run_query(query_string, directory):
    tokens = tokenize(unicode(query_string, 'utf-8'))
    query = parse(tokens)
    return query.get_value(BUILTIN_SCOPE, directory)


def _show_table(table):
    for row in table:
        print('\t'.join(row))


if __name__ == '__main__':
    main()
