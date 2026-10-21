"""
让 Django 的 MySQL 后端使用 PyMySQL 驱动。

Windows 上安装 mysqlclient 需要编译环境，PyMySQL 是纯 Python 实现，安装更方便。
这个文件会在 Django 启动时自动执行。
"""

import pymysql

# PyMySQL 会把自己伪装成 MySQLdb，Django 的 mysql 后端即可正常加载。
pymysql.install_as_MySQLdb()
