import argparse
import os
from collections import OrderedDict

from colorama import Fore

from lsql.expr import BUILTIN_CONTEXT, TaggedUnicode
from lsql.lexer import tokenize
from lsql.parser import parse

BROWN = '\x1b[33m'


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
    table = run_query(args.query_string, args.directory)
    _show_table(table)


def run_query(query_string, directory):
    tokens = tokenize(unicode(query_string, 'utf-8'))
    # TODO(aershov182): check that user hasn't passed both FROM and directory
    BUILTIN_CONTEXT['cwd'] = (directory or '.')
    query = parse(tokens)
    return query.get_value(BUILTIN_CONTEXT)


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


def _show_table(table):
    for row in table:
        # TODO(aershov182): handle unicode
        print('\t'.join(map(str, colorize(row))))


if __name__ == '__main__':
    main()
