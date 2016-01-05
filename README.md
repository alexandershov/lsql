## What is it?
It's like `find` but with SQL (work in progress)

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
| name | name of the file | a.txt |
| path | relative path to file | a.txt |
| fullpath | full path to file | /tmp/a.txt|
| size | size of file in bytes | 8234 |
| atime | access time to file | 2015-09-13T05:24:51 |
| mtime | modification time of file | 2015-09-13T05:24:51 |
| ctime | time of file's status change | 2015-09-13T05:24:51 |
| birthtime | creation time, supported on OS X only | 2015-09-13T05:24:51 |
| dir | relative path to the directory containing file| tmp |
| fulldir | full path to the directory containing file | /tmp |
| ext | extension (without dot) | txt |
| extension | same as `ext` column | txt |
| no_ext | name of the file without extension | a |
| owner | owner of file | root |
| group | group of the owner of the file | staff |
| mode | permissions mode | 0100644 |
| depth | depth of file relative to cwd | 0 for files in cwd, 1 in direct siblings of cwd, etc|
| type | type of file | one of 'file/dir/link/mount/unknown' |
| device | device | 16777220 |
| hardlinks | number of hard links to file | 1 |
| inode | inode number | 2015-09-13T05:24:51 |
| text | content of the file | whatever is in file |
| is_exec | is executable? | `true` if file is executable, `false` otherwise |
| is_executable | same as `is_exec` column | `true` if file is executable, `false` otherwise |

## Functions
| Name  | Description  | Usage | Example |
| ----  | -----------  | ----- | ------- |
| UPPER | convert string to uppercase | `lsql "select UPPER(name)"` | 'A' |
| LOWER | convert string to lowercase | `lsql "select LOWER(name)"` | 'a' |
| AGE | return age of timestamp | `lsql "select AGE(mtime)"` | '1 minute' |
| BTRIM | delete characters from the both ends of the string | `lsql "select BTRIM(name, '~')"` | 'a' |
| LENGTH | length of the string/array | `lsql "select LENGTH(lines)"` | 5 |


## Suffixes
Lsql supports number literal suffixes.
For example, to select files with size greater than 10 megabytes use: 
```sql
SELECT path WHERE size > 10mb
```

Here are all available suffixes:

| Suffix | Value | Example |
| ------ | ----- | ------- |
|k|1024 bytes|where size > 2k|
|kb|1024 bytes, alias for `k`|where size > 2kb|
|m|1024 * 1024 bytes|where size > 2mb|
|mb|1024 * 1024 bytes, alias for `mb`|where size > 2mb|
|g|1024 * 1024 * 1024 bytes|where size > 2g|
|gb|1024 * 1024 * 1024, alias for `g`|where size > 2gb|
|minute|60 seconds|where age(mtime) > 2minute|
|minutes|60 seconds, alias for `minute`|where age(mtime) > 2minutes|
|hour|60 minutes|where age(mtime) > 2hour|
|hours|60 minutes, alias for `hour`|where age(mtime) > 2hours|
|day|24 hours|where age(mtime) > 2day|
|days|24 hours, alias for `day`|where age(mtime) > 2days|
|week|7 days|where age(mtime) > 2week|
|weeks|7 days, alias for `week`|where age(mtime) > 2weeks|
|month|30 days|where age(mtime) > 2month|
|months|30 days, alias for `month`|where age(mtime) > 2months|
|year|365 days|where age(mtime) > 2year|
|years|365 days, alias for `year`|where age(mtime) > 2years|
