import os

import lsql

DIR = os.path.join(os.path.dirname(__file__), 'data')
FROM_CLAUSE = 'FROM {}'.format(DIR)

MD = ['README.md']
PY = ['small.py']


def test_simple():
    assert_query_unordered([MD, PY],
                           'SELECT name')


def test_order():
    assert_query([MD, PY],
                 'SELECT name', 'ORDER BY name')


def test_where():
    assert_query([PY],
                 'SELECT name', "WHERE extension = 'py' ORDER BY name")


def test_like():
    assert_query([MD],
                 'SELECT name', "WHERE content LIKE '%nice!%'")
    assert_query([],
                 'SELECT name', "WHERE content LIKE '%very%'")
    assert_query([MD],
                 'SELECT name', "WHERE content LIKE '%_ery%'")


def test_and():
    assert_query([PY],
                 'SELECT name', "WHERE LOWER(name) LIKE '%a%' AND extension = 'py'")


def test_len():
    assert_query(
        [PY],
        'SELECT name', 'WHERE LENGTH(lines) = 4'
    )


def assert_query(expected_results,
                 before_from,
                 after_from='',
                 from_clause=FROM_CLAUSE):
    results = get_results(before_from, after_from, from_clause)
    assert results == expected_results


def assert_query_unordered(expected_results,
                           before_from,
                           after_from='',
                           from_clause=FROM_CLAUSE):
    results = get_results(before_from, after_from, from_clause)
    assert_same_items(results, expected_results)


def get_results(before_from, after_from='', from_clause=FROM_CLAUSE):
    return list(lsql.run_query(' '.join([before_from, from_clause, after_from])))


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)
