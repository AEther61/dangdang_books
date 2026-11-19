"""
阶段性报告用：索引优化实验（真实 MySQL 8.0.46 数据）

实验对象：book / book_scale（临时放大表）
输出：EXPLAIN ANALYZE 原始计划，可直接贴进报告
"""

import pymysql

CONF = dict(host="127.0.0.1", port=3307, user="root", password="123456",
            database="dangdang_books")

Q_RANKING = "SELECT id, title, price, rating FROM {table} ORDER BY rating DESC LIMIT 20"


def explain(cur, sql, label):
    print("\n" + "=" * 70)
    print("##", label)
    print("SQL:", sql)
    print("-" * 70)
    cur.execute("EXPLAIN ANALYZE " + sql)
    for row in cur.fetchall():
        print(row[0])


def main():
    c = pymysql.connect(**CONF, autocommit=True)
    cur = c.cursor()
    cur.execute("SET SESSION cte_max_recursion_depth = 5000")

    # ---------- 实验 A：现有 120 行，有索引 vs 无索引 ----------
    explain(cur, Q_RANKING.format(table="book"), "A1 现有 120 行（idx_book_rating 存在）")

    cur.execute("ALTER TABLE book DROP INDEX idx_book_rating")
    explain(cur, Q_RANKING.format(table="book"), "A2 删除 idx_book_rating 后")
    cur.execute("CREATE INDEX idx_book_rating ON book (rating)")
    explain(cur, Q_RANKING.format(table="book"), "A3 恢复 idx_book_rating 后")

    # ---------- 实验 B：20 万行放大，无索引 vs 有索引 ----------
    cur.execute("DROP TABLE IF EXISTS book_scale")
    cur.execute("""
        CREATE TABLE book_scale (
            id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            rating DECIMAL(3,1) NOT NULL,
            publisher_id BIGINT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
        INSERT INTO book_scale (title, price, rating, publisher_id)
        SELECT CONCAT(b.title, ' #', seq.n), b.price, b.rating, b.publisher_id
        FROM book b
        JOIN (
            WITH RECURSIVE s(n) AS (
                SELECT 0 UNION ALL SELECT n + 1 FROM s WHERE n < 1666
            )
            SELECT n FROM s
        ) seq
    """)
    cur.execute("SELECT COUNT(*) FROM book_scale")
    print("\n放大表行数:", cur.fetchone()[0])

    explain(cur, Q_RANKING.format(table="book_scale"), "B1 20 万行无索引")

    cur.execute("CREATE INDEX idx_scale_rating ON book_scale (rating)")
    explain(cur, Q_RANKING.format(table="book_scale"), "B2 20 万行有索引")

    cur.execute("DROP TABLE book_scale")
    print("\n临时表已清理。")

    # ---------- 其余页面的查询计划（佐证索引设计有效） ----------
    explain(cur, """
        SELECT b.title, rs.rank_no
        FROM ranking_snapshot rs JOIN book b ON b.id = rs.book_id
        WHERE rs.snapshot_date = (SELECT MAX(snapshot_date) FROM ranking_snapshot)
          AND rs.category_id IS NULL
        ORDER BY rs.rank_no LIMIT 10
    """, "C1 最新总榜 Top10（idx_ranking_date_rank）")

    explain(cur, """
        SELECT price, recorded_at FROM price_history
        WHERE book_id = 1 ORDER BY recorded_at DESC LIMIT 12
    """, "C2 某书价格历史（idx_price_book_time）")

    c.close()


if __name__ == "__main__":
    main()
