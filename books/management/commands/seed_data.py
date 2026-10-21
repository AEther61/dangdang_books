"""
生成一套可直接演示的样例数据。

用法：
    python manage.py seed_data

会生成 120 本图书、若干作者/出版社/分类、3 个日期的总榜快照和价格历史。
重复执行会更新同一批样例数据，不会无限增加图书。
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from books.models import (
    Author,
    Book,
    BookAuthor,
    BookCategory,
    Category,
    CrawlLog,
    PriceHistory,
    Publisher,
    RankingSnapshot,
)

PUBLISHERS = [
    "人民邮电出版社",
    "机械工业出版社",
    "电子工业出版社",
    "清华大学出版社",
    "北京大学出版社",
    "中信出版社",
    "商务印书馆",
    "人民文学出版社",
    "中国青年出版社",
    "科学出版社",
    "上海译文出版社",
    "译林出版社",
]

AUTHORS = [
    "张伟", "王芳", "李娜", "刘洋", "陈静",
    "杨帆", "赵磊", "黄敏", "周涛", "吴倩",
    "徐强", "孙丽", "马超", "朱婷", "胡军",
    "郭鹏", "何静", "高翔", "林峰", "罗琳",
    "郑凯", "梁爽", "谢楠", "宋佳", "唐宁",
    "许诺", "韩雪", "冯博", "曹阳", "彭勇",
]

CATEGORIES = [
    ("计算机与互联网", "编程、数据库、人工智能等计算机相关图书"),
    ("文学小说", "中外文学作品与小说"),
    ("经济管理", "经济学、管理学与商业实务"),
    ("历史传记", "历史读物与人物传记"),
    ("哲学宗教", "哲学思想与宗教文化"),
    ("心理学", "心理学理论与应用"),
    ("艺术设计", "美术、设计与摄影"),
    ("科普读物", "自然科学与大众科普"),
    ("教育考试", "教材、考试与学习方法"),
    ("生活时尚", "健康、饮食与生活方式"),
]

SUBJECTS = [
    "Python编程", "数据库系统", "机器学习", "数据结构与算法", "Web开发",
    "操作系统", "计算机网络", "软件工程", "人工智能", "数据分析",
    "中国历史", "世界文学", "微观经济学", "管理学原理", "心理学导论",
    "哲学入门", "平面设计", "天文学基础", "英语写作", "健康饮食",
]

FORMATS = [
    "入门与实践", "进阶指南", "案例精讲",
    "核心技术与应用", "项目实战", "从入门到精通",
]

# 每个主题对应的主分类（与 SUBJECTS 一一对应）。
SUBJECT_CATEGORY = [
    "计算机与互联网", "计算机与互联网", "计算机与互联网", "计算机与互联网", "计算机与互联网",
    "计算机与互联网", "计算机与互联网", "计算机与互联网", "计算机与互联网", "计算机与互联网",
    "历史传记", "文学小说", "经济管理", "经济管理", "心理学",
    "哲学宗教", "艺术设计", "科普读物", "教育考试", "生活时尚",
]


class Command(BaseCommand):
    help = "生成 120 本图书的演示数据（含榜单快照与价格历史）"

    @transaction.atomic
    def handle(self, *args, **options):
        publisher_map = {}
        for name in PUBLISHERS:
            publisher_map[name], _ = Publisher.objects.get_or_create(name=name)

        author_map = {}
        for name in AUTHORS:
            author_map[name], _ = Author.objects.get_or_create(name=name)

        category_map = {}
        for name, description in CATEGORIES:
            category_map[name], _ = Category.objects.get_or_create(
                name=name, defaults={"description": description}
            )

        books = []
        for index in range(120):
            subject_index = index % len(SUBJECTS)
            format_index = index // len(SUBJECTS)
            title = f"{SUBJECTS[subject_index]}{FORMATS[format_index]}"
            publisher_name = PUBLISHERS[index % len(PUBLISHERS)]

            price = (Decimal("39.80") + Decimal((index * 7) % 80)).quantize(
                Decimal("0.01")
            )
            original_price = (price * Decimal("1.25")).quantize(Decimal("0.01"))
            rating = (
                Decimal("7.5") + Decimal((index * 13) % 25) / Decimal("10")
            ).quantize(Decimal("0.1"))
            publish_date = date(2025, 1, 1) + timedelta(days=(index * 17) % 540)

            book, _ = Book.objects.update_or_create(
                isbn=f"9787111{index:06d}",
                defaults={
                    "dangdang_id": f"DD{index + 1:06d}",
                    "title": title,
                    "subtitle": "",
                    "publisher": publisher_map[publisher_name],
                    "price": price,
                    "original_price": original_price,
                    "rating": rating,
                    "review_count": 120 + (index * 137) % 50000,
                    "publish_date": publish_date,
                    "cover_url": "",
                    "detail_url": f"https://product.dangdang.com/{10000000 + index * 17}.html",
                    "description": (
                        f"《{title}》围绕{SUBJECTS[subject_index]}的核心知识展开，"
                        "兼顾基础概念、典型案例和实际操作，适合课程学习与项目参考。"
                    ),
                    "is_active": True,
                },
            )
            books.append(book)

            author_names = [AUTHORS[(index * 3) % len(AUTHORS)]]
            if index % 3 == 0:
                second_author = AUTHORS[(index * 7 + 5) % len(AUTHORS)]
                if second_author not in author_names:
                    author_names.append(second_author)

            book.book_authors.all().delete()
            BookAuthor.objects.bulk_create(
                [
                    BookAuthor(book=book, author=author_map[name], author_order=order)
                    for order, name in enumerate(author_names, start=1)
                ]
            )

            book.book_categories.all().delete()
            primary_category = category_map[SUBJECT_CATEGORY[subject_index]]
            book_categories = [
                BookCategory(book=book, category=primary_category, is_primary=True)
            ]
            if index % 4 == 0:
                secondary_name = CATEGORIES[(subject_index + 3) % len(CATEGORIES)][0]
                secondary_category = category_map[secondary_name]
                if secondary_category.id != primary_category.id:
                    book_categories.append(
                        BookCategory(
                            book=book,
                            category=secondary_category,
                            is_primary=False,
                        )
                    )
            BookCategory.objects.bulk_create(book_categories)

        # 最新总榜：按评分和评论数排序，取前 50 名。
        ranked_books = list(
            Book.objects.filter(is_active=True).order_by(
                "-rating", "-review_count", "title"
            )[:50]
        )
        today = timezone.localdate()
        snapshot_offsets = [0, 1, 7]
        for offset in snapshot_offsets:
            snapshot_date = today - timedelta(days=offset)
            # 不同日期做少量轮换，让榜单历史看起来有变化。
            shift = {0: 0, 1: 3, 7: 7}[offset] % len(ranked_books) if ranked_books else 0
            ordered_books = ranked_books[shift:] + ranked_books[:shift]
            for rank, book in enumerate(ordered_books, start=1):
                RankingSnapshot.objects.update_or_create(
                    book=book,
                    category=None,
                    snapshot_date=snapshot_date,
                    defaults={"rank_no": rank},
                )

        # 每本书生成 3 条价格记录，展示价格变化。
        for book in books:
            for days_ago, delta in (
                (30, Decimal("8.00")),
                (7, Decimal("3.00")),
                (0, Decimal("0.00")),
            ):
                recorded_at = timezone.make_aware(
                    datetime.combine(today - timedelta(days=days_ago), time(9, 0))
                )
                PriceHistory.objects.update_or_create(
                    book=book,
                    recorded_at=recorded_at,
                    defaults={
                        "price": max(Decimal("9.90"), book.price + delta),
                        "source": "seed",
                    },
                )

        CrawlLog.objects.create(
            source="seed",
            status="success",
            records_found=len(books),
            records_saved=len(books),
            started_at=timezone.now() - timedelta(minutes=1),
            finished_at=timezone.now(),
            message="seed_data 生成演示数据",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"样例数据生成完成：图书 {len(books)} 本，"
                f"作者 {len(AUTHORS)} 位，出版社 {len(PUBLISHERS)} 家，"
                f"榜单快照 {len(ranked_books) * len(snapshot_offsets)} 条。"
            )
        )
