# 爬虫数据格式

爬虫组（A）把抓取结果保存为 JSONL：**每行一个 JSON 对象**，推荐文件名 `data/books.jsonl`。

最少需要：

```json
{"title": "Python编程入门与实践", "price": 59.80}
```

推荐字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 书名，必填 |
| `price` | number | 当前价格，必填 |
| `isbn` | string | ISBN，有就填 |
| `dangdang_id` | string | 当当商品 ID |
| `subtitle` | string | 副标题 |
| `publisher` | string | 出版社名称 |
| `authors` | array/string | 作者，如 `["张伟", "王芳"]` |
| `categories` | array/string | 分类，如 `["计算机与互联网"]` |
| `original_price` | number | 原价 |
| `rating` | number | 评分，0–10 |
| `review_count` | number | 评论数 |
| `publish_date` | string | `YYYY-MM-DD` |
| `cover_url` | string | 封面图片地址 |
| `detail_url` | string | 详情页地址 |
| `description` | string | 内容简介 |
| `rank` | number | 榜单排名（可选） |
| `snapshot_date` | string | 榜单日期 `YYYY-MM-DD`，不填则用今天 |
| `ranking_category` | string | 分类榜名称；不填表示总榜 |
| `recorded_at` | string | 价格采集时间，如 `2026-10-21T09:00:00+08:00` |

导入命令：

```bash
python manage.py import_books data/books.jsonl --source dangdang
```

说明：重复导入时，优先按 `isbn` 匹配已有图书；没有 ISBN 时按 `dangdang_id`，再按“书名 + 出版社”匹配。`recorded_at` 相同则更新该条价格记录，不会重复插入。
