from __future__ import division, print_function

import os

import lsql


DIR = os.path.join(os.path.dirname(__file__), 'data')


def test_simple():
    names = list(lsql.run_query("SELECT name FROM {} ORDER BY name".format(DIR)))
    assert names == [['README.md'], ['small.py']]


