from setuptools import find_packages, setup

setup(
    name='lsql',
    install_requires=[
        'colorama',
        'pyparsing',
    ],
    version='0.1',
    entry_points={
        'console_scripts': [
            'lsql = lsql:main'
        ],
    },
    packages=find_packages(),
    author='Alexander Ershov',
)
