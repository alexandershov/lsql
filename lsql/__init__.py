import argparse
import os
import re

QUERY_RE = re.compile(r"^SELECT (?P<columns>.+?)(?P<from_clause> FROM '(?P<directory>[^']+)')?$",
                      re.I)


class Stat(object):
    def __init__(self, path):
        self.path = path
        self.name = os.path.basename(path)
        self.__stat = os.stat(path)

    def __getattr__(self, name):
        return getattr(self.__stat, 'st_' + name)


# TODO: use ply for parsing
def run_query(query):
    match = QUERY_RE.match(query)
    if match is None:
        raise ValueError('bad query: {!r}'.format(query))
    columns = [column.strip() for column in match.group('columns').split(',')]
    from_clause = match.group('from_clause')
    if not from_clause:
        directory = '.'
    else:
        directory = match.group('directory')
    print('\t'.join(columns))
    for dirpath, dirnames, filenames in os.walk(directory):
        for name in filenames:
            path = os.path.join(dirpath, name)
            stat = Stat(path)
            fields = [str(getattr(stat, column)) for column in columns]
            print('\t'.join(fields))


def main():
    parser = argparse.ArgumentParser(prog='lsql', description='Search for files with SQL')
    parser.add_argument('query', help='sql query to execute, e.g "select name')
    args = parser.parse_args()
    run_query(args.query)
