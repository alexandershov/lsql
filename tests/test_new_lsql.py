# coding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

# TODO(aershov182): when done, replace test_lsql with this file
import pytest

from lsql import ast
from lsql import main
from lsql import parser

BASE_DIR = pytest.get_fixture_dir('base')


def idfn(val):
    if isinstance(val, unicode):
        return val.encode('utf-8')


# TODO(aershov182): remove assert_same_items/get_results duplication in tests

def test_select_name():
    assert_same_items(
        get_results('select name'), [
            ('small',),
            ('LICENSE',),
            ('README.md',),
            ('small.py',),
        ]
    )


@pytest.mark.parametrize('select, result', [
    ('1', 1),
    ('1.3', 1.3),
    ('1.3e2', 130),
    ('100e-2', 1),
    ('2hours', 7200),
    # checking that suffix is case-insensitive
    ('2HoUrS', 7200),
    ('+3', 3),
    ('-3', -3),
])
def test_number_literal(select, result):
    query = 'select {} limit 1'.format(select)
    expected_results = [(result,)]
    assert_same_items(
        get_results(query),
        expected_results,
    )


@pytest.mark.parametrize('query, expected_results', [
    ('select 1 + 3', ((4,),) * 4),
    ('select 1 + 7 * 3', ((22,),) * 4),
    ('select (-1-4-3) * 5', ((-40,),) * 4),
    ('select 8 / (2 * +2)', ((2,),) * 4),
])
def test_math(query, expected_results):
    assert_same_items(
        get_results(query),
        expected_results,
    )


@pytest.mark.parametrize('query, expected_results', [
    ("where ext = 'py'", [('small.py',)]),
    ("select NULL", ((ast.NULL,),) * 4),
    ("select name WHERE ext = 'py'", [('small.py',)]),
    ("select name WHERE ext = 'py' OR no_ext = 'README'",
     [('small.py',), ('README.md',)]),
    ("select name WHERE 3 >= 2 AND type = 'dir'",
     [('small',)]),

    ('select name, length(lines)', [
        ('small.py', 4),
        ('LICENSE', 1),
        ('small', ast.NULL),
        ('README.md', 1),
    ]),
    ("select name where ext IN ('py', 'md')", [
        ('small.py',),
        ('README.md',),
    ]),
    ('select name where length(lines) between 2 and 4', [
        ('small.py',),
    ]),
    ('select count(*)', [
        (4,)
    ]),
    ('select name, count(*) group by name', [
        ('small.py', 1),
        ('LICENSE', 1),
        ('small', 1),
        ('README.md', 1),
    ]),
    ("select name, count(*) group by name having name = 'small.py'", [
        ('small.py', 1),
    ]),
    ('select sum(length(lines))', [
        (6,),
    ]),
    ('select max(length(lines))', [
        (4,),
    ]),
    ('select min(length(lines))', [
        (1,),
    ]),
    ('select avg(length(lines))', [
        (6 / 3,),
    ]),
    ("select name || '_test' group by name || '_test'", [
        ('small.py_test',),
        ('LICENSE_test',),
        ('small_test',),
        ('README.md_test',),
    ]),
], ids=idfn)
def test_query(query, expected_results):
    assert_same_items(
        get_results(query),
        expected_results,
    )


def test_from():
    assert_same_items(
        get_results("select 1 FROM '{}'".format(BASE_DIR), directory=None),
        (((1,),) * 4)
    )


@pytest.mark.parametrize('query, expected_len', [
    ('select *', 4),
])
def test_result_len(query, expected_len):
    # just checking that it works
    assert len(get_results(query)) == expected_len


def test_concat():
    assert_same_items(
        get_results("select name || '_test'"), [
            ('small_test',),
            ('LICENSE_test',),
            ('README.md_test',),
            ('small.py_test',),
        ]
    )


@pytest.mark.parametrize('query, expected_results', [
    ('select fullpath',
     [(pytest.make_full_path(b'tests/data/non-ascii-paths/тест.txt'),)]),
    ('select path', [(b'tests/data/non-ascii-paths/тест.txt',)]),
    ('select name', [(b'тест.txt',)]),
    ('select no_ext', [(b'тест',)]),
])
def test_non_ascii_paths(query, expected_results):
    assert_same_items(
        get_results(query, directory=pytest.get_fixture_dir('non-ascii-paths')),
        expected_results
    )


def test_from_directory_does_not_exist():
    with pytest.raises(ast.DirectoryDoesNotExistError):
        get_results('select 1', directory='does not exist!')


def test_unknown_literal_suffix():
    with pytest.raises(parser.UnknownLiteralSuffixError):
        get_results('select 5badsuffix')


@pytest.mark.parametrize('query, expected_results', [
    ('select name, count(*) group by name order by name', [
        ('LICENSE', 1),
        ('README.md', 1),
        ('small', 1),
        ('small.py', 1),
    ]),
    ('select name, count(*) group by name order by name, count(*) DESC', [
        ('LICENSE', 1),
        ('README.md', 1),
        ('small', 1),
        ('small.py', 1),
    ]),
])
def test_group_by_order_by(query, expected_results):
    assert get_results(query) == expected_results


@pytest.mark.parametrize('query, expected_results', [
    ("select name where type = 'file' order by length(name)", [
        ('LICENSE',),
        ('small.py',),
        ('README.md',),
    ]),
    ('select name order by size limit 1', [
        ('LICENSE',)
    ]),
    ('select name order by length(lines) DESC, name ASC', [
        ('small.py',),
        ('LICENSE',),
        ('README.md',),
        ('small',),
    ]),
    ("select name, no_ext ORDER BY name LIMIT 1", [
        ('LICENSE', 'LICENSE')  # TODO(aershov182): better test
    ]),
    ("select name, no_ext ORDER BY name LIMIT 1 OFFSET 1", [
        ('README.md', 'README')
    ]),
])
def test_order_by(query, expected_results):
    assert get_results(query) == expected_results


@pytest.mark.parametrize('query', [
    # "size" is not in group by
    'select size group by name',
    # aggregate functions can't be nested
    'select max(avg(size))',
    # size + 9 is not in group by list
    'select size + 9 group by size + 8',
    # size is not in group by list
    'select name group by name order by size',
    # aggregate function in group by
    'select name group by name, count(*)',
])
def test_illegal_group_by(query):
    with pytest.raises(ast.IllegalGroupBy):
        get_results(query)


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)


def get_results(query, directory=BASE_DIR):
    # TODO: remove str(directory) and figure out how to live with unicode directories
    # in this case `DirectoryWalker.walk` will return unicode, Stat._path will be unicode and
    # Stat.path will try to decode unicode which is not supported.
    return list(main.run_query(unicode(query), str(directory)))
