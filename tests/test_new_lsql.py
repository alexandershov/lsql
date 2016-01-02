# TODO(aershov182): when done, replace test_lsql with this file

import pytest

import os

from lsql import expr
from lsql import main

DIR = os.path.join(os.path.dirname(__file__), 'data')


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
    # ('select count(*), sum(length(lines))', [(6,)])
])
def test_query(query, expected_results):
    assert_same_items(
        get_results(query),
        expected_results,
    )


def test_from():
    assert_same_items(
        get_results("select 1 FROM '{}'".format(DIR), directory=None),
        (((1,),) * 4)
    )


def test_select_star():
    # just checking that it works
    assert len(get_results('select *')) == 4


def test_concat():
    assert_same_items(
        get_results("select name || '_test'"), [
            ('small_test',),
            ('LICENSE_test',),
            ('README.md_test',),
            ('small.py_test',),
        ]
    )


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)


def get_results(query, directory=DIR):
    return list(main.run_query(query, directory))
