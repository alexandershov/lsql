from __future__ import absolute_import, division, print_function, unicode_literals

import pytest

from lsql.main import main

BASE_DIR = pytest.get_fixture_dir('base')
NON_ASCII_PATHS_DIR = pytest.get_fixture_dir('non-ascii-paths')


# we don't check results (they're checked in test_new_lsql.py)
# we just want to check that lsql.main:main doesn't throw exception
@pytest.mark.parametrize('query', [
    'select 1',
])
def test_select(query):
    run_query(query)


def run_query(query, directory=None):
    if directory is None:
        directory = BASE_DIR
    main(argv=[query, directory])
