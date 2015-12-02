from __future__ import absolute_import, division, print_function, unicode_literals

import logging

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


def pytest_addoption(parser):
    parser.addoption('--loglevel', action='store', default=None,
                     help='set logging.level. e.g: --loglevel=info')


@pytest.fixture(autouse=True, scope='session')
def loglevel(request):
    level_opt = request.config.getoption('--loglevel')
    level = NAME_TO_LOGLEVEL.get(level_opt)
    if level is not None:
        logging.basicConfig(level=level)
