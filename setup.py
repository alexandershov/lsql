from setuptools import find_packages, setup

setup(
    name='lsql',
    packages=find_packages(),
    version='0.1',
    entry_points={
        'console_scripts': [
            'lsql = lsql:main'
        ],
    },
    author='Alexander Ershov',
)
