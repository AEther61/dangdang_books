# 榜单数据格式

`data/books.jsonl` 是本项目的**标准数据集**：由 `scraper/fetch_ranking.py` 从当当畅销榜抓取，
每行一个 JSON 对象，共 **5400 条**，覆盖 **44 个分类** 和 **11 个时间周期**。

标准数据集随仓库提交，clone 后执行 `python manage.py init_demo` 即可直接导入，不需要重新爬。

## 字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 书名，必填 |
| `price` | number | 当前价格，必填 |
| `rank` | number | 在该榜单内的排名 |
| `ranking_category` | string | 榜单分类名，如 `总榜`、`童书`、`小说` |
| `ranking_period` | string | **时间维度**：月榜为 `2026-07`，当期榜为 `近7日` / `近24小时` |
| `ranking_kind` | string | 榜单类型：`month` / `recent7` / `24hours` |
| `categories` | array | 图书所属分类（与 `ranking_category` 一致） |
| `dangdang_id` | string | 当当商品 ID |
| `original_price` | number | 原价 |
| `rating` | number | 评分，0–10 |
| `review_count` | number | 评论数 |
| `authors` | array | 作者，如 `["余华"]` |
| `publisher` | string | 出版社名称 |
| `publish_date` | string | 出版日期 `YYYY-MM-DD` |
| `cover_url` | string | 封面图片地址 |
| `detail_url` | string | 详情页地址 |
| `isbn` | string | ISBN，榜单页通常没有，可留空 |
| `snapshot_date` | string | 榜单日期 `YYYY-MM-DD`，不填则由 `ranking_period` 换算 |

只有 `title` 和 `price` 是必填，其余字段缺失不影响导入。

## 时间维度说明

`ranking_period` 决定这条榜单记录对应的快照日期：

| `ranking_period` 示例 | 入库后的 `snapshot_date` |
|---|---|
| `2026-01` | 2026-01-31（该月最后一天） |
| `2026-07` | 2026-07-31 |
| `近7日` | 导入当天 |

同一本书在不同周期的排名都会保存成独立记录，可以据此分析排名变化。

## 示例

```json
{"rank": 1, "ranking_category": "总榜", "ranking_period": "2026-10", "ranking_kind": "month", "title": "盛唐繁花", "dangdang_id": "410557582", "price": "19.80", "original_price": "99.60", "rating": 5.4, "review_count": 445189, "authors": ["意林"], "publisher": "长江文艺出版社", "categories": ["总榜"]}
```

## 导入

```bash
python manage.py import_books data/books.jsonl --source dangdang
```

匹配顺序：`isbn` → `dangdang_id` → “书名 + 出版社”。

作者/分类重复会自动去重；每条记录独立事务，单条失败不影响整批。

## 重新采集

```bash
python scraper/fetch_ranking.py --all-categories --months 2026:1-10 --pages 5
python manage.py init_demo --reset
```

采集说明见项目根目录 README 第 4 章。
