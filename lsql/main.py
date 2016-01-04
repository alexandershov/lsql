from __future__ import absolute_import, division, print_function, unicode_literals


import argparse
import os
from collections import OrderedDict

from colorama import Fore

from lsql.expr import BUILTIN_CONTEXT, Context, MergedContext, TaggedUnicode
from lsql.parser import parse, tokenize

BROWN = '\x1b[33m'


def main():
    parser = argparse.ArgumentParser(
        description='SQL over filesystem',
    )
    # TODO(aershov182): maybe add_argument_group to group options by meaning (visual, behaviour etc)
    parser.add_argument(
        '-H', action='store_true',
        help='show header with column names',
        dest='with_header',
    )
    parser.add_argument('query_string', metavar='query')
    parser.add_argument(
        'directory',
        help='query working directory',
        nargs='?',
    )
    args = parser.parse_args()
    table = run_query(args.query_string, args.directory)
    _show_table(table, args.with_header)


def run_query(query_string, directory):
    tokens = tokenize(unicode(query_string, 'utf-8'))
    # TODO(aershov182): check that user hasn't passed both FROM and directory
    cwd_context = Context({'cwd': (directory or '.')})
    query = parse(tokens)
    return query.get_value(MergedContext(cwd_context, BUILTIN_CONTEXT))


def colored(text, color):
    return color + text + Fore.RESET


def colorize(row):
    colors = parse_lscolors(os.getenv('LSCOLORS') or '')
    colored_row = []
    for value in row:
        if isinstance(value, TaggedUnicode):
            for tag, color in colors.viewitems():
                if tag in value.tags:
                    value = colored(value, color)
                    break
        colored_row.append(value)
    return colored_row

# TODO: respect background, executable, bold.
def parse_lscolors(lscolors):
    """
    :param lscolors: value of $LSCOLORS env var
    :return: dictionary {tag -> color}
    """
    if not lscolors:
        return OrderedDict.fromkeys(
            ['dir', 'link', 'exec', 'file'],
            Fore.RESET
        )
    return OrderedDict([
        ('dir', lscolor_to_termcolor(lscolors[0].lower())),
        ('link', lscolor_to_termcolor(lscolors[2].lower())),
        ('exec', lscolor_to_termcolor(lscolors[8].lower())),
        ('file', Fore.RESET),
    ])


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


def _show_table(table, with_header):
    if with_header:
        print('\t'.join(table.row_type))
    for row in table:
        print('\t'.join(map(unicode, colorize(row))))


if __name__ == '__main__':
    main()
