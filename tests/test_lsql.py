import os
from colorama import Fore
import lsql

DIR = os.path.join(os.path.dirname(__file__), 'data')

SELECT_CLAUSE = 'SELECT name'
FROM_CLAUSE = "FROM '{}'".format(DIR)

MD = [lsql.colored('README.md', Fore.RESET)]
PY = [lsql.colored('small.py', Fore.RESET)]


def test_simple():
    assert_query_unordered([MD, PY])


def test_order():
    assert_query(
        [MD, PY],
        after_from='ORDER BY name',
    )


def test_where():
    assert_query(
        [PY],
        after_from="WHERE extension = 'py' ORDER BY name"
    )


def test_like():
    assert_query(
        [MD],
        after_from="WHERE text LIKE '%nice!%'"
    )

    assert_query(
        [],
        after_from="WHERE text LIKE '%very%'"
    )

    assert_query(
        [MD],
        after_from="WHERE text LIKE '%_ery%'"
    )


def test_and():
    assert_query(
        [PY],
        after_from="WHERE LOWER(name) LIKE '%a%' AND extension = 'py'"
    )


def test_len():
    assert_query(
        [PY],
        after_from='WHERE LENGTH(lines) = 4'
    )


def test_star():
    assert_query_unordered(
        [[lsql.colored('tests/data/README.md', Fore.RESET)],
         [lsql.colored('tests/data/small.py', Fore.RESET)]],
        select_clause='SELECT *'
    )

def test_no_select():
    assert_query_unordered(
        [[lsql.colored('tests/data/README.md', Fore.RESET)],
         [lsql.colored('tests/data/small.py', Fore.RESET)]],
        select_clause=''
    )


def assert_query(expected_results,
                 select_clause=SELECT_CLAUSE,
                 from_clause=FROM_CLAUSE,
                 after_from=''):
    results = get_results(select_clause=select_clause,
                          from_clause=from_clause,
                          after_from=after_from)
    assert results == expected_results


def assert_query_unordered(expected_results,
                           select_clause=SELECT_CLAUSE,
                           from_clause=FROM_CLAUSE,
                           after_from=''):
    results = get_results(select_clause=select_clause,
                          from_clause=from_clause,
                          after_from=after_from)
    assert_same_items(results, expected_results)


def get_results(select_clause=SELECT_CLAUSE, from_clause=FROM_CLAUSE, after_from=''):
    return list(lsql.run_query(' '.join([select_clause, from_clause, after_from])))


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)
