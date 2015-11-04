## What is it?
It's like `find` but with SQL (Work in progress)

## Install
```shell
git clone https://github.com/alexandershov/lsql
cd lsql && pip install .
```

## Examples
Let's select name and size of all files from the /tmp
```shell
lsql "SELECT name, size FROM '/tmp'"
```

You can omit the FROM clause and specify the directory as the command line argument:
```shell
lsql "SELECT path, size" /tmp
```

Select files from the current directory larger than 3 kilobytes:
```shell
lsql "SELECT path, size WHERE size > 3kb"
```

Select python scripts without descending into children directories:
```shell
lsql "SELECT name, size WHERE name LIKE '%.py' AND depth = 0"
```

Select python scripts which import argparse module:
```shell
lsql "SELECT path WHERE ext = 'py' AND text like '%import argparse%'"
 ```
 
`SELECT` is optional (`SELECT path` is default):
```shell
lsql "WHERE ext = 'py'"
```
 
## Limitation
* OR conditions are not supported YET. 
* Basic arithmetic is not supported YET.
* SQL support is limited YET.
 
## Columns
Let's say you're in the directory /tmp with two files
* /tmp/a.txt
* /tmp/d/b.txt

| Name  | Description  | Example |
| :---- | :----------- | ----- |
| fullpath | full path to file | /tmp/a.txt|
| size | size of file in bytes | 8234 |
| owner | owner of file | root |
| path | relative path to file | ./a.txt |
| fulldir | full path to the directory containing file | /tmp |
| dir | relative path to the directory containing file| ./ |
| name | name of the file | a.txt |
| ext | extension (without dot) | txt |
| extension | same as `ext` column | txt |
| mode | permissions mode | 0100644 |
| group | group of the owner of the file | staff |
| atime | access time to file | 2015-09-13T05:24:51 |
| mtime | modification time of file | 2015-09-13T05:24:51 |
| ctime | time of file's status change | 2015-09-13T05:24:51 |
| birthtime | creation time | 2015-09-13T05:24:51 |
| depth | depth of file relative to cwd | 0 for files in cwd, 1 in direct siblings of cwd, etc|
| type | type of file | one of 'file/dir/link/mount/unknown' |
| device | device | 16777220 |
| hardlinks | number of hard links to file | 1 |
| inode | inode number | 2015-09-13T05:24:51 |
| text | content of the file | whatever is in file |
| is_exec | is executable? | true if file is executable, false otherwise |
| is_executable | same as `is_exec` column | true if file is executable, false otherwise |
