import os
import sys


# avoiding directory coloring
os.environ['LSCOLORS'] = ''

from colorama import Fore
import pytest

import lsql

DIR = os.path.join(os.path.dirname(__file__), 'data')

FROM_CLAUSE = "FROM '{}'".format(DIR)

NO_EXT_MD = [lsql.colored('README', Fore.RESET)]
NO_EXT_PY = [lsql.colored('small', Fore.RESET)]
NO_EXT_DIR = [lsql.colored('small', Fore.RESET)]
NO_EXT_LIC = [lsql.colored('LICENSE', Fore.RESET)]
NAME_MD = [lsql.colored('README.md', Fore.RESET)]
NAME_PY = [lsql.colored('small.py', Fore.RESET)]
NAME_DIR = [lsql.colored('small', Fore.RESET)]
NAME_LIC = [lsql.colored('LICENSE', Fore.RESET)]
PATH_PY = [lsql.colored('tests/data/small.py', Fore.RESET)]
PATH_MD = [lsql.colored('tests/data/README.md', Fore.RESET)]
PATH_DIR = [lsql.colored('tests/data/small', Fore.RESET)]
PATH_LIC = [lsql.colored('tests/data/small/LICENSE', Fore.RESET)]


def test_name_column():
    assert_same_items(
        get_results(select='name'),
        [NAME_MD, NAME_PY, NAME_DIR, NAME_LIC]
    )


@pytest.mark.parametrize('order, results', [
    ('name', [NAME_LIC, NAME_MD, NAME_DIR, NAME_PY]),
    ('name ASC', [NAME_LIC, NAME_MD, NAME_DIR, NAME_PY]),
    ('name asc', [NAME_LIC, NAME_MD, NAME_DIR, NAME_PY]),
    ('name DESC', [NAME_PY, NAME_DIR, NAME_MD, NAME_LIC]),
    ('name desc', [NAME_PY, NAME_DIR, NAME_MD, NAME_LIC]),
])
def test_order_clause(order, results):
    assert get_results(order=order) == results


def test_where_clause():
    assert get_results(where="extension = 'py'", order='name') == [NAME_PY]


@pytest.mark.parametrize('where, results', [
    ("text LIKE '%nice!%'", [NAME_MD]),
    ("text LIKE '%very%'", []),
    ("text LIKE '%_ery%'", [NAME_MD]),
])
def test_like_operator(where, results):
    assert get_results(where=where) == results


@pytest.mark.parametrize('where, results', [
    ("text ILIKE '%NICE%'", [NAME_MD]),
    ("text ILIKE '%VERY%'", [NAME_MD]),
    ("text ILIKE '%BADADUM%'", []),
])
def test_ilike_operator(where, results):
    assert get_results(where=where) == results


@pytest.mark.parametrize('where, results', [
    ("text RLIKE '.*nice!.*'", [NAME_MD]),
    ("text RLIKE '.*very.*'", []),
    ("text RLIKE '.*.ery.*'", [NAME_MD]),
])
def test_rlike_operator(where, results):
    assert get_results(where=where) == results


@pytest.mark.parametrize('where, results', [
    ("text RILIKE '.*NICE!.*'", [NAME_MD]),
    ("text RILIKE '.*VERY.*'", [NAME_MD]),
    ("text RILIKE '.*.BADADUM.*'", []),
])
def test_rlike_operator(where, results):
    assert get_results(where=where) == results


@pytest.mark.parametrize('where, results', [
    ("text CONTAINS 'nice'", [NAME_MD]),
    ("text CONTAINS 'very'", []),
    ("text CONTAINS 'ery'", [NAME_MD]),
])
def test_contains_operator(where, results):
    assert get_results(where=where) == results


@pytest.mark.parametrize('where, results', [
    ("text ICONTAINS 'NICE'", [NAME_MD]),
    ("text ICONTAINS 'very'", [NAME_MD]),
    ("text ICONTAINS 'BADADUM'", []),
])
def test_icontains_operator(where, results):
    assert get_results(where=where) == results


def test_and_operator():
    assert get_results(where="LOWER(name) LIKE '%a%' AND extension = 'py'") == [NAME_PY]


def test_length_of_lines():
    assert get_results(where='LENGTH(lines) = 4') == [NAME_PY]


def test_star_column():
    # just checking that it works
    assert len(get_results(select='*')) == 4


def test_empty_select():
    assert_same_items(get_results(select=''), [PATH_PY, PATH_MD, PATH_DIR, PATH_LIC])


def test_is_exec_column():
    assert get_results(where='is_exec') == [NAME_DIR]


def test_upper_function():
    assert get_results(select='UPPER(ext)', order='UPPER(ext)') == [[''], [''], ['MD'], ['PY']]


def test_text_of_dir():
    assert get_results(select='text', where="type = 'dir'") == [['NULL']]


def test_length_of_null_is_null():
    assert get_results(select='LENGTH(text)', where="type = 'dir'") == [['NULL']]


def test_null_is_false():
    assert_same_items(
        get_results(where='text'),
        [NAME_PY, NAME_MD, NAME_LIC]
    )


def test_not_null_is_false():
    assert_same_items(
        get_results(where='NOT text'),
        []
    )


@pytest.mark.parametrize('operator, num_rows', [
    ('!=', 3),
    ('<>', 3),
    ('=', 1),
    ('==', 1),
])
def test_equality_operators(operator, num_rows):
    where = "ext {} 'py'".format(operator)
    assert len(get_results(where=where)) == num_rows


@pytest.mark.parametrize('operator, num_rows', [
    ('<', 0),
    ('<=', 0),
    ('>', 4),
    ('>=', 4),
])
def test_comparison_operators(operator, num_rows):
    where = 'size {} 0'.format(operator)
    assert len(get_results(where=where)) == num_rows


def test_ext_column():
    assert get_results(where="ext = 'py'") == [NAME_PY]


def test_no_ext_column():
    assert_same_items(
        get_results(select='no_ext'),
        [NO_EXT_PY, NO_EXT_MD, NO_EXT_DIR, NO_EXT_LIC]
    )


@pytest.mark.parametrize('column', [
    'owner',
    'group',
    'mode',
    'atime',
    'ctime',
    'device',
    'hardlinks',
    'inode',
])
def test_esoteric_columns(column):
    # it's hard to test the exact values of those columns, so we just check
    # that they work
    assert len(get_results(select=column)) == 4


# TODO: support windows if it supports st_birthtime
@pytest.mark.skipif(
    not sys.platform.startswith(('darwin', 'freebsd')),
    reason='birthtime is supported only on Mac OS X and freebsd')
def test_birthtime_column():
    assert len(get_results(select='birthtime')) == 4


@pytest.mark.parametrize('suffix, expected_value', [
    ('k', 2 ** 10),
    ('kb', 2 ** 10),
    ('m', 2 ** 20),
    ('mb', 2 ** 20),
    ('g', 2 ** 30),
    ('gb', 2 ** 30),
    ('minute', 60),
    ('minutes', 60),
    ('hour', 3600),
    ('hours', 3600),
    ('day', 86400),
    ('days', 86400),
    ('week', 86400 * 7),
    ('weeks', 86400 * 7),
    ('month', 86400 * 30),
    ('months', 86400 * 30),
    ('year', 86400 * 365),
    ('years', 86400 * 365),
])
def test_literal_suffixes(suffix, expected_value):
    assert get_results(select='1{}'.format(suffix)) == [[str(expected_value)]] * 4


def test_type_column():
    assert_same_items(
        get_results(select='type'),
        [['file'], ['file'], ['file'], ['dir']]
    )


def test_dir_column():
    assert_same_items(
        get_results(select='dir'),
        [['tests/data'], ['tests/data'], ['tests/data'], ['tests/data/small']]
    )


def test_depth_column():
    assert_same_items(
        get_results(select='depth'),
        [['0'], ['0'], ['0'], ['1']]
    )


def test_limit_clause():
    assert get_results(select='1', limit='1') == [['1']]


def test_btrim_function():
    assert get_results(select="btrim(name, 'sl')", where="type = 'dir'") == [['ma']]


def test_age_function():
    assert len(get_results(where='age(mtime) >= 0')) == 4


@pytest.mark.parametrize('select, where, results', [
    ("concat(no_ext, '.py')", "ext = 'md'", [['README.py']]),
    ("concat(name, text, '.py')", "type='dir'", [['small.py']]),
])
def test_concat_function(select, where, results):

    assert get_results(select=select, where=where) == results


def test_current_date_function():
    # just checking that it works
    assert len(get_results(select='CURRENT_DATE')) == 4


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
