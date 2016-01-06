from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from lsql.main import main

BASE_DIR = pytest.get_fixture_dir(b'base')
NON_ASCII_PATHS_DIR = pytest.get_fixture_dir('non-ascii-paths')


# We don't check results (they're checked in test_new_lsql.py).
# We just want to check that lsql.main:main never throws exception (even when query is bad).

@pytest.mark.parametrize('query', [
    # empty query is legal
    '',
    'select 1',
    "select fullpath || 'oops' where size > 0kb and ext != 'py'",
    'select name group by name',
])
def test_good_select(query):
    assert run_query(query) == 0


@pytest.mark.parametrize('query', [
    # CantTokenizeError: unclosed string literal
    "select 'text",
    # CantTokenizeError: other
    "select `",
    # UnknownLiteralSuffixError
    "select 1unknown",
    # NotImplementedTokenError: as is not implemented
    "select name as name_alias",
    # UnexpectedTokenError
    "order 'unexpected'"
    # OperatorExpectedError: value token instead of operator
    'select 3 3',
    # OperatorExpectedError: keyword token instead of operator
    'select 3 from',
    # ValueExpectedError: operator token instead of value
    'select + *',
    # ValueExpectedError: keyword token instead of value
    'select 3 + from',
    # UnexpectedEndError
    'select 3 +',
])
def test_bad_select(query):
    assert run_query(query) == 1


def run_query(query, directory=None):
    if directory is None:
        directory = BASE_DIR
    # TODO: handle str/unicode insanity
    return main(argv=[query, str(directory)])
