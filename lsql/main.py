from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import argparse
import os
import sys

from colorama import Fore

from lsql.expr import BUILTIN_CONTEXT, Context, MergedContext, TaggedUnicode
from lsql.parser import parse, tokenize
from lsql.expr import DirectoryDoesNotExistError
from lsql import get_version

FORE_BROWN = '\x1b[33m'

GITHUB = 'https://github.com/alexandershov/lsql'


# TODO(aershov182): this should just to print_message when --no-color is passed
def print_warning(text):
    print_message(colored(text, Fore.RED))


# TODO(aershov182): this should just to print_message when --no-color is passed
def print_error(text):
    print_warning(text)


def print_message(text):
    print(text, file=sys.stderr)


def main():
    args = _get_parser().parse_args()
    try:
        table = run_query(args.query_string, args.directory)
        _show_table(table, args.with_header, args.color)
    except DirectoryDoesNotExistError as exc:
        print_error("directory '{}' doesn't exist".format(exc.path))


def _get_parser():
    parser = argparse.ArgumentParser(
        description="It's like /usr/bin/find but with SQL",
    )
    output_options = parser.add_argument_group(title='output options')
    output_options.add_argument(
        '-H', '--header', action='store_true',
        help='show header with column names',
        dest='with_header',
    )
    output_options.add_argument(
        '-C', '--no-color', action='store_false',
        help="don't colorize output",
        dest='color',
    )

    parser.add_argument(
        '--version', action='version', version='%(prog)s version {}'.format(get_version())
    )
    parser.add_argument(
        'query_string',
        help=(
            'For example: "where size > 10mb" '
            'For more examples see {}/README.md'
        ).format(GITHUB),
        metavar='query',
    )
    parser.add_argument(
        'directory',
        help=(
            "Do query on this directory. "
            "Note that you can't specify FROM clause and directory argument together"
        ),
        nargs='?',
    )
    return parser


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
        'e': FORE_BROWN,
        'f': Fore.MAGENTA,
        'g': Fore.CYAN,
        'h': Fore.LIGHTWHITE_EX,
    }
    return color_mapping.get(lscolor, Fore.RESET)


def _show_table(table, with_header, with_color):
    if with_header:
        print('\t'.join(table.row_type))
    for row in table:
        if with_color:
            row = colorize(row)
        print('\t'.join(map(unicode, row)))


if __name__ == '__main__':
    main()
