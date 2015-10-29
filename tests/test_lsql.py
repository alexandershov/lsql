import os


# avoiding directory coloring
os.environ['LSCOLORS'] = ''

from colorama import Fore
import pytest

import lsql

DIR = os.path.join(os.path.dirname(__file__), 'data')

FROM_CLAUSE = "FROM '{}'".format(DIR)

NAME_MD = [lsql.colored('README.md', Fore.RESET)]
NAME_PY = [lsql.colored('small.py', Fore.RESET)]
NAME_DIR = [lsql.colored('small', Fore.RESET)]
NAME_LIC = [lsql.colored('LICENSE', Fore.RESET)]
PATH_PY = [lsql.colored('tests/data/small.py', Fore.RESET)]
PATH_MD = [lsql.colored('tests/data/README.md', Fore.RESET)]
PATH_DIR = [lsql.colored('tests/data/small', Fore.RESET)]
PATH_LIC = [lsql.colored('tests/data/small/LICENSE', Fore.RESET)]


def test_simple():
    assert_same_items(
        get_results(select='name'),
        [NAME_MD, NAME_PY, NAME_DIR, NAME_LIC]
    )


@pytest.mark.parametrize('order, results', [
    ('name', [NAME_LIC, NAME_MD, NAME_DIR, NAME_PY]),
    ('name ASC', [NAME_LIC, NAME_MD, NAME_DIR, NAME_PY]),
    ('name DESC', [NAME_PY, NAME_DIR, NAME_MD, NAME_LIC]),
])
def test_order(order, results):
    assert get_results(order=order) == results


def test_where():
    assert get_results(where="extension = 'py'", order='name') == [NAME_PY]


@pytest.mark.parametrize('where, results', [
    ("text LIKE '%nice!%'", [NAME_MD]),
    ("text LIKE '%very%'", []),
    ("text LIKE '%_ery%'", [NAME_MD]),
])
def test_like(where, results):
    assert get_results(where=where) == results


@pytest.mark.parametrize('where, results', [
    ("text RLIKE '.*nice!.*'", [NAME_MD]),
    ("text RLIKE '.*very.*'", []),
    ("text RLIKE '.*.ery.*'", [NAME_MD]),
])
def test_rlike(where, results):
    assert get_results(where=where) == results


def test_and():
    assert get_results(where="LOWER(name) LIKE '%a%' AND extension = 'py'") == [NAME_PY]


def test_len():
    assert get_results(where='LENGTH(lines) = 4') == [NAME_PY]


def test_star():
    assert_same_items(get_results(select='*'), [PATH_PY, PATH_MD, PATH_DIR, PATH_LIC])


def test_empty_select():
    assert_same_items(get_results(select=''), [PATH_PY, PATH_MD, PATH_DIR, PATH_LIC])


def test_is_exec():
    assert get_results(where='is_exec') == [NAME_DIR]


def test_upper():
    assert get_results(select='UPPER(ext)', order='UPPER(ext)') == [[''], [''], ['MD'], ['PY']]


def test_suffix():
    assert get_results(select='1kb') == [['1024']] * 4


def test_type():
    assert_same_items(
        get_results(select='type'),
        [['file'], ['file'], ['file'], ['dir']]
    )


def test_limit():
    assert get_results(select='1', limit='1') == [['1']]


def get_results(select='name', from_clause=FROM_CLAUSE, where='', order='', limit=''):
    clauses = []
    if select:
        clauses.extend(['SELECT', select])
    clauses.append(from_clause)
    if where:
        clauses.extend(['WHERE', where])
    if order:
        clauses.extend(['ORDER BY', order])
    if limit:
        clauses.extend(['LIMIT', limit])
    return list(lsql.run_query(' '.join(clauses)))


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)
