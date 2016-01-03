# coding: utf-8

# TODO(aershov182): when done, replace test_lsql with this file

import pytest

import os

from lsql import expr
from lsql import main


def get_fixture_dir(fixture_name):
    return os.path.join(os.path.dirname(__file__), 'data', fixture_name)


def make_full_path(rel_path):
    return os.path.join(os.getcwd(), rel_path)


BASE_DIR = get_fixture_dir('base')


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


@pytest.mark.parametrize('query, expected_results', [
    ('select 1', ((1,),) * 4),
    ('select 1.3', ((1.3,),) * 4),
    ('select 1.3e2', ((130.0,),) * 4),
    ('select 2hours', ((7200,),) * 4),
])
def test_number_literal(query, expected_results):
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
    ("select NULL", ((expr.NULL,),) * 4),
    ("select name WHERE ext = 'py'", [('small.py',)]),
    ("select name WHERE ext = 'py' OR no_ext = 'README'",
     [('small.py',), ('README.md',)]),
    ("select name WHERE 3 >= 2 AND type = 'dir'",
     [('small',)]),
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
    ('select name, length(lines)', [
        ('small.py', 4),
        ('LICENSE', 1),
        ('small', expr.NULL),
        ('README.md', 1),
    ]),
    ("select name where ext IN ('py', 'md')", [
        ('small.py',),
        ('README.md',),
    ]),
    ('select name where length(lines) between 2 and 4', [
        ('small.py',),
    ]),
    ('select count(name)', [(4,)]),
    # ('select count(name), sum(length(lines))', [
    #     (4, 6),
    # ])
])
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
    ('select avg(size)', 1),
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
     [(make_full_path(u'tests/data/non-ascii-paths/тест.txt'),)]),
    ('select path', [(u'tests/data/non-ascii-paths/тест.txt',)]),
    ('select name', [(u'тест.txt',)]),
    ('select no_ext', [(u'тест',)]),
])
def test_non_ascii_paths(query, expected_results):
    assert_same_items(
        get_results(query, directory=get_fixture_dir('non-ascii-paths')),
        expected_results
    )


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)


def get_results(query, directory=BASE_DIR):
    return list(main.run_query(query, directory))
