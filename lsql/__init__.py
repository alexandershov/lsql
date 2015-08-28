from collections import OrderedDict
from itertools import count, izip
import argparse

import os
import re

QUERY_RE = re.compile(r"^SELECT (?P<columns>.+?)(?P<from_clause> FROM '(?P<directory>[^']+)')?$",
                      re.I)


class Stat(object):
    # name -> priority
    ATTRS = OrderedDict(izip(['name', 'size', 'ctime'], count()))

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.__stat = os.stat(path)

    def get_value(self, name):
        if name not in Stat.ATTRS:
            raise ValueError('unknown attr: {!r}'.format(name))
        return getattr(self, name)

    def __getattr__(self, name):
        return getattr(self.__stat, 'st_' + name)


# TODO: use ply for parsing
def run_query(query, directory):
    match = QUERY_RE.match(query)
    if match is None:
        raise ValueError('bad query: {!r}'.format(query))
    if match.group('columns') == '*':
        columns = list(Stat.ATTRS)
    else:
        columns = [column.strip() for column in match.group('columns').split(',')]
    from_clause = match.group('from_clause')
    if from_clause:
        if directory:
            raise ValueError("You can't specify FROM and directory as cmd arg")
        directory = match.group('directory')
    print('\t'.join(columns))
    for dirpath, dirnames, filenames in os.walk(directory):
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = Stat(path)
            fields = [str(stat.get_value(column)) for column in columns]
            print('\t'.join(fields))


def main():
    parser = argparse.ArgumentParser(prog='lsql', description='Search for files with SQL')
    parser.add_argument('query', help='sql query to execute, e.g "select name')
    parser.add_argument('directory', help='directory to search in', nargs='?')
    args = parser.parse_args()
    run_query(args.query, args.directory)
