## What is it?
Query your file system with SQL (Work in progress)

## Install
```shell
git clone https://github.com/alexandershov/lsql
cd lsql && pip install .
```

## Examples
Let's select name and size of all files from the /tmp
```shell
lsql "SELECT name, size FROM /tmp"
```

You can omit the FROM clause and specify the directory as the command line argument:
```shell
lsql "SELECT name, size" /tmp
```

Select files from the current directory larger than 3 kilobytes:
```shell
lsql "SELECT name, size WHERE size > 3kb"
```

Select .py files without descending into children directories:
```shell
lsql "SELECT name, size WHERE name LIKE '%.py' AND depth = 0"
```
