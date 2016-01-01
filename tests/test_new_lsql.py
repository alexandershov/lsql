# TODO(aershov182): when done, replace test_lsql with this file

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


def assert_same_items(seq_x, seq_y):
    assert sorted(seq_x) == sorted(seq_y)


def get_results(query):
    return list(main.run_query(query, DIR))
