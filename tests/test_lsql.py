import os

import lsql

DIR = os.path.join(os.path.dirname(__file__), 'data')


def test_simple():
    assert_query([['README.md'], ['small.py']],
                 'SELECT name', 'ORDER BY name')


def test_where():
    assert_query([['small.py']],
                 'SELECT name', "WHERE extension = 'py' ORDER BY name")


def assert_query(expected_results,
                 before_from,
                 after_from='',
                 from_clause='FROM {}'.format(DIR)):
    results = list(lsql.run_query(' '.join([before_from, from_clause, after_from])))
    assert results == expected_results
