from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import argparse
import os
import textwrap
import sys

from colorama import Fore

from lsql.ast import BUILTIN_CONTEXT, Context, CombinedContext, TaggedStr
from lsql.parser import parse, tokenize
from lsql import ast
from lsql import get_version
from lsql import parser

FORE_BROWN = '\x1b[33m'

COLOR_ARG_CHOICES = (
    'never',
    'always',
    'auto',  # Color stdout only if it's a tty. Always color stderr
)

GITHUB = 'https://github.com/alexandershov/lsql'
GITHUB_ISSUES = '{}/issues'.format(GITHUB)
GITHUB_README = '{}/blob/master/README.md'.format(GITHUB)

WIDTH = 80

SUCCESS_CODE = 0
FAILURE_CODE = 1


# TODO: split this class into 2. One should be about errors/warnings/messages, another - about colored_column()
class Printer(object):
    def __init__(self, width=WIDTH):
        self._width = width

    def colored(self, color, text, start=0, end=None):
        return text

    def warning(self, text, start=0, end=None):
        return text

    def error(self, text, start=0, end=None):
        return text

    def colored_column(self, value):
        return value

    def new_line(self):
        self.show_message('')

    def show_message(self, text):
        print(textwrap.fill(text, self._width), file=sys.stderr)

    def show_error(self, text, start=0, end=None):
        self.show_message(self.error(text=text, start=start, end=end))

    def show_warning(self, text, start=0, end=None):
        self.show_message(self.warning(text=text, start=start, end=end))

    def show_token_error(self, text, token):
        self.show_error(text, start=token.start, end=token.end)


class ColoredPrinter(Printer):
    def __init__(self, tag_colors, width=WIDTH):
        super(ColoredPrinter, self).__init__(width)
        self._tag_colors = tag_colors

    def colored(self, color, text, start=0, end=None):
        assert isinstance(text, unicode)
        if end is None:
            end = len(text)
        return text[:start] + color + text[start:end] + Fore.RESET + text[end:]

    def warning(self, text, start=0, end=None):
        return self.colored(color=Fore.RESET, text=text, start=start, end=end)

    def error(self, text, start=0, end=None):
        return self.colored(color=Fore.RED, text=text, start=start, end=end)

    def colored_column(self, column_value):
        # TODO: how to do it without isinstance?
        if isinstance(column_value, TaggedStr):
            for tag, color in self._tag_colors.viewitems():
                if tag in column_value.tags:
                    # TODO: don't hardcode utf-8, figure out encodings
                    return self.colored(color, column_value.decode('utf-8'))
        return column_value


# TODO: what? NoColored is inherited from Colored?
class NoColoredColumnPrinter(ColoredPrinter):
    def colored_column(self, column_value):
        return column_value


def _get_printer(stdout, color):
    tag_colors = parse_lscolors(os.getenv('LSCOLORS') or '')
    if color == 'always':
        return ColoredPrinter(tag_colors)
    elif color == 'never':
        return Printer()
    elif color == 'auto':
        if stdout.isatty():
            return ColoredPrinter(tag_colors)
        else:
            return NoColoredColumnPrinter(tag_colors)
    else:
        raise ValueError("Oops, bad color value '{}', should be one of {!r}".format(color, COLOR_ARG_CHOICES))


def main(argv=None):
    args = _get_args_parser().parse_args(argv)
    printer = _get_printer(sys.stdout, args.color)
    try:
        table = run_query(args.query_string, args.directory)
        _show_table(table, args.with_header, printer)
        return SUCCESS_CODE
    except parser.CantTokenizeError as exc:
        if args.query_string[exc.pos] == "'":
            printer.show_message("Probably unterminated single quoted string starting at {}:".format(
                get_context(args.query_string, exc.pos)))
        else:
            printer.show_message("Can't tokenize query starting at `{}`: ".format(get_context(
                args.query_string, exc.pos)))
        printer.show_error(args.query_string, exc.pos)
    except parser.UnknownLiteralSuffixError as exc:
        printer.show_message("Unknown number literal suffix `{}`:".format(exc.suffix))

        printer.show_token_error(args.query_string, exc.token)
        printer.show_message('Known suffixes are: <{}>'.format(', '.join(exc.known_suffixes)))
        printer.new_line()
        printer.show_message('For gory details take a look at the documentation: {}#suffixes'.format(GITHUB_README))
    except parser.NotImplementedTokenError as exc:
        token_text = exc.match.group().upper()
        printer.show_message('Sorry, but {} is not implemented (yet):'.format(token_text))
        # TODO: do something better than match stuff (probably, exception should have some Token in it)
        printer.show_error(args.query_string, start=exc.match.start(), end=exc.match.end())
        printer.new_line()
        printer.show_message(
            'If you want lsql to support {}, '
            'then please create an issue (or pull request!): {}'.format(token_text, GITHUB_ISSUES)
        )
    except parser.UnexpectedTokenError as exc:
        if isinstance(exc.actual_token, parser.EndQueryToken):
            printer.show_message("Expected '{}', but got end of query.".format(
                exc.expected_token_class.get_human_name()))
        else:
            printer.show_message("Expected '{}', but got `{}`: ".format(
                exc.expected_token_class.get_human_name(), exc.actual_token.text))
            printer.show_error(args.query_string, start=exc.actual_token.start, end=exc.actual_token.end)
        suggest_to_create_issue_or_pull_request(printer)
    except parser.OperatorExpectedError as exc:
        printer.show_message('Expected operator, got `{}`:'.format(exc.token.text))
        printer.show_token_error(args.query_string, exc.token)
        suggest_to_create_issue_or_pull_request(printer)
    except parser.ValueExpectedError as exc:
        printer.show_message('Expected value, got `{}`:'.format(exc.token.text))
        printer.show_token_error(args.query_string, exc.token)
        suggest_to_create_issue_or_pull_request(printer)
    except parser.UnexpectedEndError:
        # TODO: handle it better: tell what's expected.
        printer.show_message('Unexpected end of query.')
        suggest_to_create_issue_or_pull_request(printer)
    except ast.DirectoryDoesNotExistError as exc:
        printer.show_error("directory '{}' doesn't exist".format(exc.path))
    return FAILURE_CODE


# TODO: rename, because pun with ast.Context
def get_context(string, start, max_len=10):
    context = string[start:start + max_len]
    if start + max_len >= len(string):
        return context
    return context + '...'


def suggest_to_create_issue_or_pull_request(printer):
    """
    :type printer: Printer
    """
    printer.new_line()
    printer.show_message("If you think that's a bug, then you're absolutely wrong!")
    printer.show_message('Just kidding. It can be a bug.')
    # TODO: better wording
    printer.show_message('Please create an issue (or pull request!): {}'.format(GITHUB_ISSUES))
    printer.show_message('Thank you.')


def _get_args_parser():
    arg_parser = argparse.ArgumentParser(
        description="It's like /usr/bin/find but with SQL",
    )
    output_options = arg_parser.add_argument_group(title='output options')
    output_options.add_argument(
        '--header', action='store_true',
        help='show header with column names',
        dest='with_header',
    )
    output_options.add_argument(
        '--color',
        # TODO: handle u'' prefixes when getting error in command line. Maybe create a separate class
        # TODO: ... ColorChoice and handle it there?
        choices=COLOR_ARG_CHOICES,
        default='auto',
        help=(
            "colorize output. The possible values of this option are: 'never', 'always', and 'auto'"
        )
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
    assert isinstance(query_string, unicode)
    tokens = tokenize(query_string)
    # TODO(aershov182): check that user hasn't passed both FROM and directory
    # TODO: b'.'? Handle TaggedStr issues inside of the ast.DirectoryWalker
    cwd_context = Context({'cwd': (directory or b'.')})
    query = parse(tokens)
    return query.get_value(CombinedContext(cwd_context, BUILTIN_CONTEXT))


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
        print_row(table.row_type)
    for row in table:
        colored_row = [colorizer.colored_column(column) for column in row]
        print_row(colored_row)


def print_row(row):
    # we need b'\t' so resulting string will not be unicode
    print(b'\t'.join(_printable_unicode(column) for column in row))


def _printable_unicode(x):
    if not isinstance(x, unicode):
        x = unicode(x)
    return x.encode('utf-8')


if __name__ == '__main__':
    sys.exit(main())
