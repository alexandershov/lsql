# TODO(aershov182): when done, replace test_lsql with this file

import pytest

import os

from lsql import main

DIR = os.path.join(os.path.dirname(__file__), 'data')


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
    ('select 1', ((1,),) * 4)
])
def test_number_literal(query, expected_results):
    assert_same_items(
        get_results(query),
        expected_results,
    )


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


def get_results(query):
    return list(main.run_query(query, DIR))
