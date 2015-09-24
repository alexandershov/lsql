import os

import lsql


DIR = os.path.join(os.path.dirname(__file__), 'data')


def test_simple():
    names = list(lsql.run_query("SELECT name FROM {} ORDER BY name".format(DIR)))
    assert names == [['README.md'], ['small.py']]


def test_where():
    names = list(lsql.run_query("SELECT name FROM {} WHERE extension = 'py' ORDER BY name".format(DIR)))
    assert names == [['small.py']]
