from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os

import pytest

NAME_TO_LOGLEVEL = {
    'notset': logging.NOTSET,
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warn': logging.WARN,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


def get_fixture_dir(fixture_name):
    return os.path.join(os.path.dirname(__file__), 'data', fixture_name)


def make_full_path(rel_path):
    return os.path.join(os.getcwd(), rel_path)


def pytest_addoption(parser):
    parser.addoption('--loglevel', action='store', default=None,
                     help='set logging.level. e.g: --loglevel=info')


@pytest.fixture(autouse=True, scope='session')
def loglevel(request):
    level_opt = request.config.getoption('--loglevel')
    level = NAME_TO_LOGLEVEL.get(level_opt)
    if level is not None:
        logging.basicConfig(level=level)


def pytest_namespace():
    return {
        'get_fixture_dir': get_fixture_dir,
        'make_full_path': make_full_path,
    }
