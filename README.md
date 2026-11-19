# 当当网畅销图书信息管理与分析

《高级数据库开发》课程小组项目。使用 **Django + MySQL** 完成图书数据的采集、存储、展示和简单分析。

**数据来源：真实爬取。** 仓库自带 5400 条当当畅销榜数据（44 个分类 + 2026 年 1~10 月月榜），`data/books.jsonl` 即为标准数据集，clone 后无需重新爬取。`seed_data.py` 的模拟数据仅作为离线兜底保留。

当前版本以“能演示”为目标：**真实榜单数据 + 3 个核心页面**，不做登录、不做自定义增删改后台、不做 PPT 和演示视频。

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
│       ├── init_demo.py      # 一键建表+导入数据
│       ├── seed_data.py      # 生成 120 条模拟数据（备用）
│       └── import_books.py   # 导入 JSONL 榜单数据
├── scraper/
│   └── fetch_ranking.py      # 当当榜单采集脚本
├── templates/                # 页面模板
├── static/css/style.css
├── data/                     # 榜单数据（JSONL）
├── docs/                     # E-R 图、表结构说明、实验脚本
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
cd <项目目录>/dangdang_books
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3.3 配置 `.env`

从模板复制一份，再改成你本机 MySQL 的密码和端口：

```bash
copy .env.example .env
```

```ini
DB_NAME=dangdang_books
DB_USER=root
DB_PASSWORD=你的密码
DB_HOST=127.0.0.1
DB_PORT=3306
```

`.env` 已加入 `.gitignore`，不要提交到 GitHub。需要重置时参考 `.env.example`。

> 如果本机 MySQL 8.0 不在默认 3306（比如另装了实例），把 `DB_PORT` 改成实际端口即可。

### 3.4 一键初始化数据（推荐）

建表 + 导入榜单数据 + 补价格历史，**一条命令搞定**：

```bash
python manage.py init_demo
```

这条命令读取仓库里的 `data/books.jsonl`（**5400 条真实爬取的当当榜单数据，已随仓库提交，不用重新爬**），完成：

1. `migrate` 建表
2. `import_books` 导入图书、作者、出版社、分类、榜单快照
3. 为每本书补一条初始价格记录

重复执行不会重复插入；想彻底重置为仓库里的标准数据：

```bash
python manage.py init_demo --reset
```

初始化完成后库里有：

| 内容 | 数量 |
|---|---|
| 图书 | 4467 |
| 作者 | 4922 |
| 出版社 | 372 |
| 排行榜分类 | 44（总榜 + 43 个一级分类） |
| 榜单记录 | 5400（含 2026 年 1~10 月月榜 + 近 7 日榜） |
| 时间周期 | 11（10 个月榜 + 当期近 7 日） |
| 价格历史 | 4467 |
| 采集日志 | 1 |

> 离线兜底：`python manage.py migrate` + `python manage.py seed_data` 会生成 120 条**模拟**数据，仅在没有网络、需要快速看页面时使用，**不是**项目的标准数据。

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

本项目可以直接使用**本机 Python 解释器**（3.12），不需要单独建虚拟环境。

1. 先确认依赖已装到本机 Python：

   ```bash
   python -m pip install -r requirements.txt
   ```

2. `File → Settings → Project: 高级数据库 → Python Interpreter`，选择 `Add Interpreter → Add Local Interpreter → System Interpreter`
3. 解释器路径选本机 Python，例如 `C:\Users\<用户名>\AppData\Local\Programs\Python\Python312\python.exe`
4. 打开右上角的运行配置下拉框，选 **`dangdang_books`**（已预置的 Django Server 配置）直接运行

`dangdang_books` 这个运行配置已经设置好：

- Script：`dangdang_books/manage.py`，参数 `runserver`
- Working directory：`dangdang_books/`
- 数据库连接自动从 `.env` 读取，不需要在 PyCharm 里另配环境变量

> 如果习惯用虚拟环境，`python -m venv .venv` 后把解释器指向 `.venv\Scripts\python.exe` 也可以，两者效果一致。

注意：`templates/` 下的是 **Django 模板**，双击只能查看/编辑源码，不能像普通 HTML 一样直接预览。要看页面效果，必须启动 Django 后访问 <http://127.0.0.1:8000/>。

### 3.7 在 PyCharm 的 Database 面板中查看数据（可选）

答辩时需要现场查表，可以加一个数据源：

| 项 | 值 |
|---|---|
| Host | `127.0.0.1` |
| Port | `3307`（注意不是 3306） |
| User | `root` |
| Password | 与 `.env` 中 `DB_PASSWORD` 一致 |
| Database | `dangdang_books` |

端口填错会连到另一个 MySQL 实例，看不到本项目的表。

## 4. 数据来源与采集

### 4.1 标准数据集

`data/books.jsonl` 是本项目的**标准数据集**，已随仓库提交，`init_demo` 直接读取它。

- 来源：当当网畅销书排行榜，**全部分类 + 时间维度（月榜）**
- 规模：**5400 条榜单记录，4469 本图书，44 个分类，11 个时间周期**
- 字段：排名、分类、周期、书名、当当 ID、现价、原价、评分、评论数、作者、出版社、出版日期、封面、详情页链接
- 字段说明见 [`data/README.md`](data/README.md)

**时间维度**：抓取 2026 年 1~10 月的月榜（每月 100 条），加上当期「近 7 日」榜（4400 条）。同一本书在不同月份的排名都会保留，可做排名变化分析。

| 时间周期 | 记录数 |
|---|---|
| 2026-01 ~ 2026-10（月榜各 100 条） | 1000 |
| 近 7 日（44 个分类 × 100 条） | 4400 |

**分类覆盖**：总榜 + 43 个一级分类（童书、小说、文学、历史、计算机/网络、哲学/宗教、医学、法律、建筑、农业/林业等），每个分类各 100 条。

各分类分布（近 7 日榜，每类 100 条）：

| 分类 | 条数 | 分类 | 条数 |
|---|---|---|---|
| 总榜 | 100 | 心理学 | 100 |
| 童书 | 100 | 青春文学 | 100 |
| 中小学用书 | 100 | 管理 | 100 |
| 小说 | 100 | 社会科学 | 100 |
| 文学 | 100 | 政治军事 | 100 |
| 外语 | 100 | 古籍 | 100 |
| 历史 | 100 | 亲子家教 | 100 |
| 动漫幽默 | 100 | 科普读物 | 100 |
| 哲学宗教 | 100 | 传记 | 100 |
| 成功励志 | 100 | 保健养生 | 100 |
| 艺术 | 100 | 法律 / 教材 / 经济 | 各 100 |

完整 43 个分类见 `data/books.jsonl` 的 `categories` 字段。

### 4.2 重新采集

需要更新数据时再跑采集脚本：

```bash
# 全部分类 × 5 页 + 2026 年 1-10 月月榜（当前标准数据的抓法）
python scraper/fetch_ranking.py --all-categories --months 2026:1-10 --pages 5

# 只抓总榜 5 页（100 条）
python scraper/fetch_ranking.py

# 只抓指定分类
python scraper/fetch_ranking.py --only 童书,小说,历史 --pages 3

# 断点续爬：中断后重跑会自动跳过已抓过的组合
python scraper/fetch_ranking.py --all-categories --months 2026:1-10 --resume
```

实现要点：

- 分类编码**不硬编码**，运行时从榜单页导航自动发现
- 页面是 GBK 编码，已显式指定
- **从第 2 页起页面 title 会带“第N页_”前缀**，解析分类名前需先剥离
- 部分商品同时显示秒杀价和活动价，只取第一段作为现价
- 月榜无数据的月份（如未结束的当月）自动跳过
- 每页间隔 0.8 秒；只抓公开榜单信息，不绕过登录/验证码

如果采集后分类名有变化，可执行 `python scraper/normalize_categories.py` 统一分类名。

### 4.3 导入任意 JSONL

```bash
python manage.py import_books data/books.jsonl --source dangdang
```

导入逻辑：

- 优先按 `isbn` 匹配已有图书，再按 `dangdang_id`，最后按“书名 + 出版社”
- 可同时写入作者、分类、榜单快照和价格历史
- 作者/分类重复会自动去重（如“罗广斌,罗广斌著”）
- 每条记录独立事务，单条失败不影响整批，失败明细写入 `crawl_log`

## 5. 核心页面

| 页面 | 路由 | 数据来源 |
|---|---|---|
| 仪表盘 | `/` | `book`、`publisher`、`author`、`ranking_snapshot` 聚合查询 |
| 图书列表 | `/books/` | `book` + `book_author` + `book_category`，支持搜索/分类/排序/分页 |
| 图书详情 | `/books/<id>/` | `book`、`ranking_snapshot`、`price_history` |

## 6. 验收检查

```text
[ ] python manage.py check 无报错
[ ] python manage.py init_demo 无报错
[ ] 数据来自 MySQL，不是 SQLite
[ ] 至少有 100 条图书数据（当前为 4467 本图书、5400 条榜单记录）
[ ] 数据来自真实爬取，data/books.jsonl 可追溯
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

还没有导入数据，执行：

```bash
python manage.py init_demo
```

### 数据量不对 / 想恢复成仓库里的标准数据

```bash
python manage.py init_demo --reset
```

这会把业务表清空后重新导入 `data/books.jsonl`。

### 想更新成最新的榜单数据

```bash
python scraper/fetch_ranking.py --categories 10 --pages 5
python manage.py init_demo --reset
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

# 复制环境变量模板，并填写自己电脑的 MySQL 密码和端口
copy .env.example .env

# 建空库
mysql -u root -p < scripts/init_db.sql

# 一条命令建表 + 导入仓库里的 5400 条真实榜单数据
python manage.py init_demo

# 启动
python manage.py runserver
```

PowerShell 用户把激活命令换成：

```powershell
.venv\Scripts\Activate.ps1
```

`.env` 不进入 Git，每个人使用自己的本地数据库密码。

> **不需要重新跑爬虫。** `data/books.jsonl` 已随仓库提交，`init_demo` 直接读它。只有想更新榜单时才执行 `scraper/fetch_ranking.py`。

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
