from collections import OrderedDict
from pwd import getpwuid
import argparse

from pyparsing import alphas, CaselessKeyword, Group, delimitedList, Optional, QuotedString, Word

import os


class Stat(object):
    ATTRS = OrderedDict.fromkeys(['name', 'size', 'owner', 'ctime'])

    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.__stat = os.stat(path)

    @property
    def owner(self):
        return getpwuid(self.__stat.st_uid).pw_name

    def get_value(self, name):
        if name not in Stat.ATTRS:
            raise ValueError('unknown attr: {!r}'.format(name))
        return getattr(self, name)

    def __getattr__(self, name):
        return getattr(self.__stat, 'st_' + name)


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
    print('\t'.join(columns))
    for dirpath, dirnames, filenames in os.walk(directory):
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = Stat(path)
            fields = [str(stat.get_value(column)) for column in columns]
            print('\t'.join(fields))


def get_grammar():
    columns = (Group(delimitedList(Word(alphas))) | '*').setResultsName('columns')
    from_clause = CaselessKeyword('FROM') + QuotedString("'").setResultsName('directory')
    return (CaselessKeyword('SELECT') + columns
            + Optional(from_clause))


def main():
    parser = argparse.ArgumentParser(prog='lsql', description='Search for files with SQL')
    parser.add_argument('query', help='sql query to execute, e.g "select name')
    parser.add_argument('directory', help='directory to search in', nargs='?')
    args = parser.parse_args()
    run_query(args.query, args.directory)
