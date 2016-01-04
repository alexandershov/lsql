from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import argparse
import os
import sys

from colorama import Fore

from lsql.expr import BUILTIN_CONTEXT, Context, MergedContext, TaggedUnicode
from lsql.parser import parse, tokenize
from lsql import expr
from lsql import get_version
from lsql import parser

FORE_BROWN = '\x1b[33m'

GITHUB = 'https://github.com/alexandershov/lsql'


class Printer(object):
    def colored(self, color, text, start=0, end=None):
        return text

    def warning(self, text, start=0, end=None):
        return text

    def error(self, text, start=0, end=None):
        return text

    def auto_colored(self, value):
        return value

    def show_message(self, text):
        print(text, file=sys.stderr)

    def show_error(self, text, start=0, end=None):
        self.show_message(self.error(text=text, start=start, end=end))

    def show_warning(self, text, start=0, end=None):
        self.show_message(self.warning(text=text, start=start, end=end))


class ColoredPrinter(Printer):
    def __init__(self, tag_colors):
        self._tag_colors = tag_colors

    def colored(self, color, text, start=0, end=None):
        assert isinstance(text, unicode)
        if end is None:
            end = len(text)
        return text[:start] + color + text[start:end] + Fore.RESET + text[end:]

    def warning(self, text, start=0, end=None):
        return self.colored(color=Fore.RED, text=text, start=start, end=end)

    def error(self, text, start=0, end=None):
        return self.colored(color=Fore.RED, text=text, start=start, end=end)

    def auto_colored(self, value):
        if isinstance(value, TaggedUnicode):
            for tag, color in self._tag_colors.viewitems():
                if tag in value.tags:
                    return self.colored(color, value)
        return value


def _get_printer(with_color):
    if with_color:
        return ColoredPrinter(parse_lscolors(os.getenv('LSCOLORS') or ''))
    return Printer()


def main():
    args = _get_arg_parser().parse_args()
    printer = _get_printer(args.color)
    try:
        table = run_query(args.query_string, args.directory)
        _show_table(table, args.with_header, printer)
    except parser.CantTokenizeError as exc:
        if exc.string[exc.pos] == "'":
            printer.show_message('Probably unterminated quoted string at position {:d}:'.format(exc.pos))
        else:
            printer.show_message("Can't tokenize query at position {:d}:".format(exc.pos))
        printer.show_error(exc.string, exc.pos)
    except parser.UnknownLiteralSuffixError as exc:
        printer.show_message("Unknown number literal suffix '{}':".format(exc.suffix))
        # TODO: add link to documentation where all suffixes are described
        printer.show_error(args.query_string, exc.token.start, exc.token.end)
        printer.show_message('Known suffixes are: <{}>'.format(', '.join(exc.known_suffixes)))
    except expr.DirectoryDoesNotExistError as exc:
        printer.show_error("directory '{}' doesn't exist".format(exc.path))


def _get_arg_parser():
    arg_parser = argparse.ArgumentParser(
            description="It's like /usr/bin/find but with SQL",
    )
    output_options = arg_parser.add_argument_group(title='output options')
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

    arg_parser.add_argument(
            '--version', action='version', version='%(prog)s version {}'.format(get_version())
    )
    arg_parser.add_argument(
            'query_string',
            type=unicode,  # TODO: check that it works & error handling when passed non-ascii symbols in command line
            help=(
                'For example: "where size > 10mb" '
                'For more examples see {}/README.md'
            ).format(GITHUB),
            metavar='query',
    )
    arg_parser.add_argument(
            'directory',
            help=(
                "Do query on this directory. "
                "Note that you can't specify FROM clause and directory argument together"
            ),
            nargs='?',
    )
    return arg_parser


def run_query(query_string, directory):
    tokens = tokenize(query_string)
    # TODO(aershov182): check that user hasn't passed both FROM and directory
    cwd_context = Context({'cwd': (directory or '.')})
    query = parse(tokens)
    return query.get_value(MergedContext(cwd_context, BUILTIN_CONTEXT))


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


def _show_table(table, with_header, colorizer):
    if with_header:
        print('\t'.join(table.row_type))
    for row in table:
        colored_row = [unicode(colorizer.auto_colored(column)) for column in row]
        print('\t'.join(colored_row))


if __name__ == '__main__':
    main()
