from setuptools import find_packages, setup

import lsql

setup(
    name='lsql',
    install_requires=[
        'colorama',
        'pyparsing',
    ],
    version=lsql.get_version(),
    entry_points={
        'console_scripts': [
            'lsql = lsql:main'
        ],
    },
    packages=find_packages(),
    author='Alexander Ershov',
)
