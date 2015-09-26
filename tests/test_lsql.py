import os

import lsql

DIR = os.path.join(os.path.dirname(__file__), 'data')
FROM_CLAUSE = 'FROM {}'.format(DIR)


def test_simple():
    results = get_results('SELECT name')
    assert_same_items([['README.md'], ['small.py']], results)


def test_order():
    assert_query([['README.md'], ['small.py']],
                 'SELECT name', 'ORDER BY name')


def test_where():
    assert_query([['small.py']],
                 'SELECT name', "WHERE extension = 'py' ORDER BY name")


def test_like():
    assert_query([['README.md']],
                 'SELECT name', "WHERE content LIKE '%nice!%'")
    assert_query([],
                 'SELECT name', "WHERE content LIKE '%very%'")
    assert_query([['README.md']],
                 'SELECT name', "WHERE content LIKE '%_ery%'")


def assert_query(expected_results,
                 before_from,
                 after_from='',
                 from_clause=FROM_CLAUSE):
    results = get_results(before_from, after_from, from_clause)
    assert results == expected_results


def get_results(before_from, after_from='', from_clause=FROM_CLAUSE):
    return list(lsql.run_query(' '.join([before_from, from_clause, after_from])))


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)
