## What is it?
Query your file system with SQL (Work in progress)

## Install
```shell
git clone https://github.com/alexandershov/lsql
cd lsql && pip install .
```

## Use 
```shell
lsql "SELECT name, size FROM '/tmp'"
lsql "SELECT name, size" /tmp
```
