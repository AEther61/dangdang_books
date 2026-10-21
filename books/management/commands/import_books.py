"""
从 JSONL 文件导入爬虫数据。

用法：
    python manage.py import_books data/books.jsonl
    python manage.py import_books data/books.jsonl --source dangdang

JSONL 每行一个 JSON 对象，最少需要 title 和 price。字段说明见 data/README.md。
"""

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

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


def _as_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).replace("，", ",").replace("、", ",").split(",") if item.strip()]


def _to_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


class Command(BaseCommand):
    help = "从 JSONL 文件导入图书数据（爬虫输出）"

    def add_arguments(self, parser):
        parser.add_argument(
            "path",
            nargs="?",
            default="data/books.jsonl",
            help="JSONL 文件路径，默认 data/books.jsonl",
        )
        parser.add_argument(
            "--source",
            default="dangdang",
            help="数据来源标识，默认 dangdang",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.is_absolute():
            path = settings.BASE_DIR / path

        if not path.exists():
            raise CommandError(f"文件不存在：{path}")

        source = options["source"]
        found = 0
        saved = 0
        errors = []

        with path.open("r", encoding="utf-8") as file:
            for line_no, line in enumerate(file, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                found += 1
                try:
                    item = json.loads(line)
                    self._import_item(item, source)
                    saved += 1
                except Exception as exc:  # 单条数据失败不影响后续记录
                    errors.append(f"第 {line_no} 行：{exc}")

        CrawlLog.objects.create(
            source=source,
            status="partial" if errors else "success",
            records_found=found,
            records_saved=saved,
            finished_at=timezone.now(),
            message="\n".join(errors[:20]),
        )

        if errors:
            self.stdout.write(self.style.WARNING(f"导入完成，但有 {len(errors)} 条失败："))
            for message in errors[:20]:
                self.stdout.write(f"  - {message}")
            self.stdout.write(f"成功导入 {saved} / {found} 条。")
        else:
            self.stdout.write(self.style.SUCCESS(f"导入完成：{saved} 条。"))

    def _import_item(self, item, source):
        title = str(item.get("title") or "").strip()
        if not title:
            raise ValueError("缺少 title")

        price = _to_decimal(item.get("price"))
        if price is None:
            raise ValueError("缺少有效的 price")

        isbn = str(item.get("isbn") or "").strip() or None
        dangdang_id = str(item.get("dangdang_id") or "").strip() or None

        publisher = None
        publisher_name = str(item.get("publisher") or "").strip()
        if publisher_name:
            publisher, _ = Publisher.objects.get_or_create(name=publisher_name)

        book = None
        if isbn:
            book = Book.objects.filter(isbn=isbn).first()
        if book is None and dangdang_id:
            book = Book.objects.filter(dangdang_id=dangdang_id).first()
        if book is None:
            book = Book.objects.filter(title=title, publisher=publisher).first()

        fields = {
            "title": title,
            "price": price,
            "isbn": isbn,
            "dangdang_id": dangdang_id,
            "publisher": publisher,
            "subtitle": str(item.get("subtitle") or "").strip(),
            "original_price": _to_decimal(item.get("original_price")),
            "rating": _to_decimal(item.get("rating")),
            "review_count": int(item.get("review_count") or 0),
            "publish_date": parse_date(str(item.get("publish_date"))) if item.get("publish_date") else None,
            "cover_url": str(item.get("cover_url") or "").strip(),
            "detail_url": str(item.get("detail_url") or "").strip(),
            "description": str(item.get("description") or "").strip(),
            "is_active": True,
        }

        if book is None:
            book = Book.objects.create(**fields)
        else:
            for field, value in fields.items():
                # 爬虫没提供的可选字段不覆盖数据库里的旧值。
                if field in ("title", "price"):
                    setattr(book, field, value)
                elif field in ("publisher", "isbn", "dangdang_id"):
                    if value:
                        setattr(book, field, value)
                elif item.get(field) not in (None, ""):
                    setattr(book, field, value)
            book.save()

        if "authors" in item:
            author_names = _as_list(item.get("authors"))
            book.book_authors.all().delete()
            for order, name in enumerate(author_names, start=1):
                author, _ = Author.objects.get_or_create(name=name)
                BookAuthor.objects.create(book=book, author=author, author_order=order)

        if "categories" in item:
            category_names = _as_list(item.get("categories"))
            book.book_categories.all().delete()
            for order, name in enumerate(category_names):
                category, _ = Category.objects.get_or_create(name=name)
                BookCategory.objects.create(
                    book=book, category=category, is_primary=(order == 0)
                )

        rank = item.get("rank")
        if rank not in (None, ""):
            snapshot_date = (
                parse_date(str(item.get("snapshot_date")))
                if item.get("snapshot_date")
                else timezone.localdate()
            )
            ranking_category = None
            ranking_category_name = str(item.get("ranking_category") or "").strip()
            if ranking_category_name:
                ranking_category, _ = Category.objects.get_or_create(
                    name=ranking_category_name
                )
            RankingSnapshot.objects.update_or_create(
                book=book,
                category=ranking_category,
                snapshot_date=snapshot_date,
                defaults={"rank_no": int(rank)},
            )

        if item.get("recorded_at"):
            recorded_at = parse_datetime(str(item["recorded_at"]))
            if recorded_at is None:
                raise ValueError("recorded_at 不是有效的时间格式")
            if timezone.is_naive(recorded_at):
                recorded_at = timezone.make_aware(recorded_at)
            PriceHistory.objects.update_or_create(
                book=book,
                recorded_at=recorded_at,
                defaults={"price": price, "source": source},
            )
