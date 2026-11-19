"""
一条命令初始化演示环境：建表 + 导入榜单数据 + 补价格历史。

用法：
    python manage.py init_demo              # 用 data/books.jsonl
    python manage.py init_demo --reset      # 先清空业务表再导入

适合别人 clone 项目后直接跑起来，不需要手工执行多个脚本。
"""

from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from books.models import Book, PriceHistory


class Command(BaseCommand):
    help = "一键初始化演示数据：migrate + 导入 data/books.jsonl + 补价格历史"

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            default="data/books.jsonl",
            help="榜单 JSONL 路径，默认 data/books.jsonl",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="导入前先清空业务表（会删除现有数据）",
        )

    def handle(self, *args, **options):
        data_path = Path(options["data"])
        if not data_path.is_absolute():
            data_path = settings.BASE_DIR / data_path
        if not data_path.exists():
            self.stderr.write(f"找不到数据文件：{data_path}")
            return

        self.stdout.write("[1/3] 建表 ...")
        call_command("migrate", verbosity=0)

        if options["reset"]:
            self.stdout.write("[2/4] 清空业务表 ...")
            self._reset()

        self.stdout.write("[2/3] 导入榜单数据 ...")
        call_command("import_books", str(data_path), source="dangdang")

        self.stdout.write("[3/3] 补价格历史 ...")
        created = self._seed_price_history()
        self.stdout.write(
            self.style.SUCCESS(
                f"完成：图书 {Book.objects.count()} 本，新增价格记录 {created} 条。"
            )
        )

    def _reset(self):
        from django.db import connection

        tables = [
            "price_history",
            "ranking_snapshot",
            "book_category",
            "book_author",
            "book",
            "category",
            "author",
            "publisher",
            "crawl_log",
        ]
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in tables:
                cursor.execute(f"TRUNCATE TABLE `{table}`")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")

    def _seed_price_history(self):
        now = timezone.now()
        created = 0
        for book in Book.objects.all():
            if not PriceHistory.objects.filter(book=book).exists():
                PriceHistory.objects.create(
                    book=book,
                    price=book.price,
                    recorded_at=now,
                    source="dangdang",
                )
                created += 1
        return created
