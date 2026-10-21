"""
仪表盘用的分析查询。

简单查询放在 views 里用 ORM；这里用原生 SQL 演示聚合、分组和连接，
也方便答辩时直接讲“这个数字来自哪条 SQL”。
"""

from django.db import connection


def _fetch_all(sql, params=None):
    """执行查询并返回字典列表。"""
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_dashboard_data():
    stats = _fetch_all(
        """
        SELECT
            (SELECT COUNT(*) FROM book WHERE is_active = 1) AS book_count,
            (SELECT COUNT(*) FROM publisher) AS publisher_count,
            (SELECT COUNT(*) FROM author) AS author_count,
            (SELECT ROUND(AVG(price), 2) FROM book WHERE is_active = 1) AS avg_price,
            (SELECT COUNT(DISTINCT snapshot_date) FROM ranking_snapshot) AS snapshot_days
        """
    )[0]

    latest_snapshot_date = _fetch_all(
        "SELECT MAX(snapshot_date) AS latest FROM ranking_snapshot"
    )[0]["latest"]

    top_publishers = _fetch_all(
        """
        SELECT p.name AS name, COUNT(*) AS value
        FROM book b
        JOIN publisher p ON p.id = b.publisher_id
        WHERE b.is_active = 1
        GROUP BY p.id, p.name
        ORDER BY value DESC, p.name ASC
        LIMIT 8
        """
    )

    price_bands = _fetch_all(
        """
        SELECT
            CASE
                WHEN price < 40 THEN '40元以下'
                WHEN price < 60 THEN '40-60元'
                WHEN price < 80 THEN '60-80元'
                WHEN price < 100 THEN '80-100元'
                ELSE '100元以上'
            END AS name,
            COUNT(*) AS value,
            MIN(price) AS min_price
        FROM book
        WHERE is_active = 1
        GROUP BY
            CASE
                WHEN price < 40 THEN '40元以下'
                WHEN price < 60 THEN '40-60元'
                WHEN price < 80 THEN '60-80元'
                WHEN price < 100 THEN '80-100元'
                ELSE '100元以上'
            END
        ORDER BY min_price ASC
        """
    )

    top_books = []
    if latest_snapshot_date:
        top_books = _fetch_all(
            """
            SELECT b.id, b.title, b.price, b.rating, rs.rank_no
            FROM ranking_snapshot rs
            JOIN book b ON b.id = rs.book_id
            WHERE rs.snapshot_date = %s
              AND rs.category_id IS NULL
              AND b.is_active = 1
            ORDER BY rs.rank_no ASC
            LIMIT 10
            """,
            [latest_snapshot_date],
        )

    return {
        "stats": stats,
        "latest_snapshot_date": latest_snapshot_date,
        "top_books": top_books,
        "publisher_chart": {
            "labels": [row["name"] for row in top_publishers],
            "values": [row["value"] for row in top_publishers],
        },
        "price_chart": {
            "labels": [row["name"] for row in price_bands],
            "values": [row["value"] for row in price_bands],
        },
    }
