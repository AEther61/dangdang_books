# 当当网畅销图书信息管理与分析

《高级数据库开发》课程小组项目。使用 **Django + MySQL** 完成图书数据的存储、展示和简单分析。

当前版本以“能演示”为目标：**爬虫/样例数据 + 3 个核心页面**，不做登录、不做自定义增删改后台、不做 PPT 和演示视频。

## 1. 技术栈

| 组件 | 版本/说明 |
|---|---|
| Python | 3.10+（本机为 3.13） |
| Django | 6.0.4 |
| MySQL | 8.0+，库名 `dangdang_books` |
| 驱动 | PyMySQL |
| 页面 | Django Templates + Bootstrap 5 CDN |
| 图表 | ECharts CDN |
| 数据访问 | 常规查询用 Django ORM，仪表盘统计用原生 SQL |

## 2. 目录结构

```text
dangdang_books/
├── manage.py
├── requirements.txt
├── .env.example              # 环境变量模板
├── config/                   # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── __init__.py           # 注册 PyMySQL
├── books/                    # 核心应用
│   ├── models.py             # 9 张表
│   ├── views.py
│   ├── urls.py
│   ├── queries.py            # 仪表盘原生 SQL
│   ├── admin.py
│   └── management/commands/
│       ├── seed_data.py      # 生成 120 条样例数据
│       └── import_books.py   # 导入爬虫 JSONL
├── templates/                # 页面模板
├── static/css/style.css
├── data/                     # 爬虫数据（JSONL）
├── docs/                     # E-R 图、表结构说明
└── scripts/init_db.sql
```

## 3. 快速启动

### 3.1 创建 MySQL 数据库

```bash
mysql -u root -p < scripts/init_db.sql
```

如果 `mysql` 不在 PATH 中，用完整路径，例如：

```bash
"D:\Develop\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p < scripts/init_db.sql
```

也可以手动在 MySQL 客户端执行：

```sql
CREATE DATABASE IF NOT EXISTS dangdang_books
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
```

### 3.2 安装依赖

建议使用虚拟环境（可选）：

```bash
cd D:\School\AdvancedDatabaseDevelopment\dangdang_books
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3.3 配置 `.env`

项目里已有一份 `.env`，把 `DB_PASSWORD` 改成你本机 MySQL 的密码：

```ini
DB_NAME=dangdang_books
DB_USER=root
DB_PASSWORD=你的密码
DB_HOST=127.0.0.1
DB_PORT=3306
```

`.env` 已加入 `.gitignore`，不要提交到 GitHub。需要重置时参考 `.env.example`。

### 3.4 建表并生成样例数据

```bash
python manage.py migrate
python manage.py seed_data
```

`seed_data` 会生成：

- 120 本图书
- 30 位作者、12 家出版社、10 个分类
- 3 个日期的总榜快照（每天前 50 名）
- 每本书 3 条价格历史
- 1 条采集日志

重复执行会更新同一批样例图书，不会无限增加。

### 3.5 启动

```bash
python manage.py runserver
```

打开：

- 仪表盘：<http://127.0.0.1:8000/>
- 图书列表：<http://127.0.0.1:8000/books/>
- 图书详情：从列表点进任意一本书
- 后台管理：<http://127.0.0.1:8000/admin/>（可选，先执行 `python manage.py createsuperuser`）

### 3.6 在 PyCharm 中运行

项目已在根目录创建 `.venv` 虚拟环境并装好依赖。PyCharm 打开项目后如果提示没有解释器：

1. `File → Settings → Project: dangdang_books → Python Interpreter`
2. 选择 `Add Interpreter → Add Local Interpreter → Existing`
3. 解释器路径选 `D:\School\AdvancedDatabaseDevelopment\dangdang_books\.venv\Scripts\python.exe`
4. 确定后，直接运行已有的 `dangdang_books` Django 配置即可

注意：`templates/` 下的是 **Django 模板**，双击只能查看/编辑源码，不能像普通 HTML 一样直接预览。要看页面效果，必须启动 Django 后访问 <http://127.0.0.1:8000/>。

## 4. 爬虫数据导入

爬虫组把结果保存为 JSONL（每行一个 JSON），字段说明见 [`data/README.md`](data/README.md)。

```bash
python manage.py import_books data/books.jsonl --source dangdang
```

导入逻辑：

- 优先按 `isbn` 匹配已有图书
- 没有 ISBN 时按 `dangdang_id` 匹配
- 再按“书名 + 出版社”匹配
- 可同时写入作者、分类、榜单快照和价格历史

即使爬虫暂时不可用，`seed_data` 也能保证验收时有 100+ 条数据。

## 5. 核心页面

| 页面 | 路由 | 数据来源 |
|---|---|---|
| 仪表盘 | `/` | `book`、`publisher`、`author`、`ranking_snapshot` 聚合查询 |
| 图书列表 | `/books/` | `book` + `book_author` + `book_category`，支持搜索/分类/排序/分页 |
| 图书详情 | `/books/<id>/` | `book`、`ranking_snapshot`、`price_history` |

## 6. 验收检查

```text
[ ] python manage.py check 无报错
[ ] python manage.py migrate 无报错
[ ] 数据来自 MySQL，不是 SQLite
[ ] 至少有 100 条图书数据
[ ] /            仪表盘能打开，有数字卡片和图表
[ ] /books/      列表能显示数据、搜索、分类筛选、分页
[ ] /books/<id>/ 详情能显示基本信息、榜单、价格历史
[ ] 能画出 E-R 图，讲清每张表存什么
[ ] 能现场执行 1–2 条 SQL 查询
```

E-R 图、表结构说明和索引优化实验见 [`docs/数据库设计.md`](docs/数据库设计.md)。

## 7. 常见问题

### `Access denied for user 'root'@'localhost'`

`.env` 里的 `DB_PASSWORD` 不正确。确认 MySQL root 密码后修改 `.env`，再执行 `python manage.py migrate`。

### `No module named 'MySQLdb'`

没有安装 PyMySQL，或 `config/__init__.py` 没有执行驱动注册：

```bash
pip install PyMySQL
```

### `Unknown database 'dangdang_books'`

还没有建库，先执行 `scripts/init_db.sql`。

### 页面提示暂无数据

执行：

```bash
python manage.py seed_data
```

### 端口被占用

```bash
python manage.py runserver 8001
```

## 8. 项目约定

- **数据库结构以 `books/models.py` 为准**，需要提交 SQL 时用 `mysqldump --no-data` 导出。
- 不实现登录和自定义 CRUD，数据维护使用 Django Admin。
- 任务书只作参考，实际开发允许交叉和调整。
- 验收前 2–3 天冻结功能，只修 bug，不加页面。

## 9. 小组协作流程（Git 分支）

### 9.1 仓库所有者：邀请组员

1. 打开 GitHub 仓库的 **Settings**
2. 左侧选择 **Collaborators**（新版界面为 **Access → Collaborators**）
3. 点击 **Add people**
4. 输入组员的 GitHub 用户名或绑定邮箱
5. 角色选择 **Write**（可以 clone、commit、push）
6. 发送邀请

组员在 GitHub 通知页或邮件里点击 **Accept invitation** 后，才拥有推送权限。

> 把组员的 GitHub 用户名收集好，不要通过密码共享账号。

### 9.2 组员首次拉取和初始化

```bash
git clone https://github.com/AEther61/dangdang_books.git
cd dangdang_books

# 创建虚拟环境（Windows cmd）
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板，并填写自己电脑的 MySQL 密码
copy .env.example .env

# 建库、建表、生成样例数据
mysql -u root -p < scripts/init_db.sql
python manage.py migrate
python manage.py seed_data

# 启动
python manage.py runserver
```

PowerShell 用户把激活命令换成：

```powershell
.venv\Scripts\Activate.ps1
```

`.env` 不进入 Git，每个人使用自己的本地数据库密码。

### 9.3 每次开发：先同步，再开分支

```bash
# 1. 切到主分支并拉取最新代码
git switch main
git pull origin main

# 2. 新建自己的功能分支（名字按功能取）
git switch -c feature/book-list

# 3. 修改代码、本地测试
python manage.py check
python manage.py runserver

# 4. 提交
git add .
git commit -m "完成图书列表搜索和分页"

# 5. 推送到 GitHub
git push -u origin feature/book-list
```

分支命名建议：

| 前缀 | 用途 | 示例 |
|---|---|---|
| `feature/` | 新功能 | `feature/book-detail` |
| `fix/` | 修 bug | `fix/dashboard-sql` |
| `docs/` | 文档 | `docs/er-diagram` |

### 9.4 发起 Pull Request 并合并

1. 推送分支后，GitHub 会提示 **Compare & pull request**，点击它
2. `base` 选 `main`，`compare` 选自己的功能分支
3. 填写改动说明，点击 **Create pull request**
4. 由仓库所有者或其他组员检查后点击 **Merge pull request**
5. 合并后删除远程功能分支

合并完成后，每个人本地更新：

```bash
git switch main
git pull origin main
git branch -d feature/book-list
```

### 9.5 协作注意事项

- 每次开新分支前先 `git pull origin main`，避免基于旧代码开发。
- 一个分支只做一件事，提交信息写清楚做了什么。
- **不要提交** `.env`、`.venv/`、`.idea/`、`__pycache__/`，这些已经在 `.gitignore` 中。
- 数据库密码只保存在各自电脑的 `.env` 里，不要发到群里或写进代码。
- 如果 `git push` 被拒绝，先 `git pull --rebase origin main`，解决冲突后再推送。
- 验收前 2–3 天冻结功能，只修 bug。
