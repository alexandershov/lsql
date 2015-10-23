import os
from colorama import Fore
import lsql

DIR = os.path.join(os.path.dirname(__file__), 'data')

DEFAULT_SELECT = 'SELECT name'
FROM_CLAUSE = "FROM '{}'".format(DIR)

NAME_MD = [lsql.colored('README.md', Fore.RESET)]
NAME_PY = [lsql.colored('small.py', Fore.RESET)]
PATH_PY = [lsql.colored('tests/data/small.py', Fore.RESET)]
PATH_MD = [lsql.colored('tests/data/README.md', Fore.RESET)]


def test_simple():
    assert_same_items(
        get_results(select=DEFAULT_SELECT),
        [NAME_MD, NAME_PY]
    )


def test_order():
    assert get_results(order='name') == [NAME_MD, NAME_PY]


def test_where():
    assert get_results(where="extension = 'py'", order='name') == [NAME_PY]


def test_like():
    assert get_results(where="text LIKE '%nice!%'") == [NAME_MD]
    assert get_results(where="text LIKE '%very%'") == []
    assert get_results(where="text LIKE '%_ery%'") == [NAME_MD]


def test_rlike():
    assert get_results(where="text RLIKE '.*nice!.*'") == [NAME_MD]
    assert get_results(where="text RLIKE '.*very.*'") == []
    assert get_results(where="text RLIKE '.*.ery.*'") == [NAME_MD]


def test_and():
    assert get_results(where="LOWER(name) LIKE '%a%' AND extension = 'py'") == [NAME_PY]


def test_len():
    assert get_results(where='LENGTH(lines) = 4') == [NAME_PY]


def test_star():
    assert_same_items(get_results(select='SELECT *'), [PATH_PY, PATH_MD])


def test_no_select():
    assert_same_items(get_results(select=''), [PATH_PY, PATH_MD])


def test_is_exec():
    assert get_results(where='is_exec') == []


def get_results(select=DEFAULT_SELECT, from_clause=FROM_CLAUSE, where='', order=''):
    if where:
        where = 'WHERE ' + where
    if order:
        order = 'ORDER BY ' + order
    return list(lsql.run_query(' '.join([select, from_clause, where, order])))


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)
