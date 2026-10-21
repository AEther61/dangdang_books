from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Publisher(models.Model):
    """出版社。"""

    name = models.CharField("出版社名称", max_length=100, unique=True)
    website = models.URLField("官网", max_length=255, blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "publisher"
        verbose_name = "出版社"
        verbose_name_plural = "出版社"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    """作者。"""

    name = models.CharField("作者姓名", max_length=100, unique=True)
    bio = models.TextField("作者简介", blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "author"
        verbose_name = "作者"
        verbose_name_plural = "作者"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    """图书主表，保存图书的基本信息和当前价格/评分。"""

    dangdang_id = models.CharField(
        "当当商品ID", max_length=32, unique=True, null=True, blank=True
    )
    title = models.CharField("书名", max_length=200)
    subtitle = models.CharField("副标题", max_length=200, blank=True, default="")
    isbn = models.CharField(
        "ISBN", max_length=20, unique=True, null=True, blank=True
    )
    publisher = models.ForeignKey(
        Publisher,
        verbose_name="出版社",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
    )
    price = models.DecimalField("当前价格", max_digits=10, decimal_places=2)
    original_price = models.DecimalField(
        "原价", max_digits=10, decimal_places=2, null=True, blank=True
    )
    rating = models.DecimalField(
        "评分",
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("10"))],
    )
    review_count = models.PositiveIntegerField("评论数", default=0)
    publish_date = models.DateField("出版日期", null=True, blank=True)
    cover_url = models.URLField("封面地址", max_length=500, blank=True, default="")
    detail_url = models.URLField("详情页地址", max_length=500, blank=True, default="")
    description = models.TextField("内容简介", blank=True, default="")
    is_active = models.BooleanField("是否有效", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    authors = models.ManyToManyField(
        Author, through="BookAuthor", related_name="books", verbose_name="作者"
    )
    categories = models.ManyToManyField(
        "Category", through="BookCategory", related_name="books", verbose_name="分类"
    )

    class Meta:
        db_table = "book"
        verbose_name = "图书"
        verbose_name_plural = "图书"
        ordering = ["-rating", "-review_count", "title"]
        indexes = [
            models.Index(fields=["title"], name="idx_book_title"),
            models.Index(fields=["publisher"], name="idx_book_publisher"),
            models.Index(fields=["price"], name="idx_book_price"),
            models.Index(fields=["-rating"], name="idx_book_rating"),
            models.Index(fields=["publish_date"], name="idx_book_publish_date"),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # 空字符串会破坏 UNIQUE 约束（MySQL 允许多个 NULL，但不允许多个空串）。
        if self.isbn == "":
            self.isbn = None
        if self.dangdang_id == "":
            self.dangdang_id = None
        super().save(*args, **kwargs)

    @property
    def discount(self):
        """返回折扣，例如 7.5 表示 7.5 折；没有原价时返回 None。"""
        if not self.original_price or self.original_price <= 0:
            return None
        return (self.price / self.original_price * Decimal("10")).quantize(
            Decimal("0.1")
        )


class BookAuthor(models.Model):
    """图书-作者关联表（多对多，并记录作者顺序）。"""

    book = models.ForeignKey(
        Book, verbose_name="图书", on_delete=models.CASCADE, related_name="book_authors"
    )
    author = models.ForeignKey(
        Author, verbose_name="作者", on_delete=models.CASCADE, related_name="book_authors"
    )
    author_order = models.PositiveSmallIntegerField("作者顺序", default=1)

    class Meta:
        db_table = "book_author"
        verbose_name = "图书作者"
        verbose_name_plural = "图书作者"
        constraints = [
            models.UniqueConstraint(
                fields=["book", "author"], name="uniq_book_author"
            )
        ]
        indexes = [
            models.Index(fields=["author"], name="idx_bookauthor_author"),
        ]
        ordering = ["book", "author_order"]

    def __str__(self):
        return f"{self.book} - {self.author}"


class Category(models.Model):
    """图书分类，支持父子分类。"""

    name = models.CharField("分类名称", max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="父分类",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField("分类说明", blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "category"
        verbose_name = "分类"
        verbose_name_plural = "分类"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BookCategory(models.Model):
    """图书-分类关联表（多对多）。"""

    book = models.ForeignKey(
        Book, verbose_name="图书", on_delete=models.CASCADE, related_name="book_categories"
    )
    category = models.ForeignKey(
        Category,
        verbose_name="分类",
        on_delete=models.CASCADE,
        related_name="book_categories",
    )
    is_primary = models.BooleanField("是否主分类", default=False)

    class Meta:
        db_table = "book_category"
        verbose_name = "图书分类"
        verbose_name_plural = "图书分类"
        constraints = [
            models.UniqueConstraint(
                fields=["book", "category"], name="uniq_book_category"
            )
        ]
        indexes = [
            models.Index(fields=["category"], name="idx_bookcategory_category"),
        ]

    def __str__(self):
        return f"{self.book} - {self.category}"


class RankingSnapshot(models.Model):
    """榜单快照：某本书在某天某个分类下的排名；category 为空表示总榜。"""

    book = models.ForeignKey(
        Book,
        verbose_name="图书",
        on_delete=models.CASCADE,
        related_name="ranking_snapshots",
    )
    category = models.ForeignKey(
        Category,
        verbose_name="分类",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ranking_snapshots",
    )
    rank_no = models.PositiveIntegerField("排名")
    snapshot_date = models.DateField("快照日期", default=timezone.localdate)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "ranking_snapshot"
        verbose_name = "榜单快照"
        verbose_name_plural = "榜单快照"
        ordering = ["-snapshot_date", "rank_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "category", "snapshot_date"],
                name="uniq_ranking_book_cat_date",
            )
        ]
        indexes = [
            models.Index(
                fields=["snapshot_date", "rank_no"], name="idx_ranking_date_rank"
            ),
            models.Index(
                fields=["book", "-snapshot_date"], name="idx_ranking_book_date"
            ),
        ]

    def __str__(self):
        category = self.category.name if self.category else "总榜"
        return f"{self.snapshot_date} {category} 第{self.rank_no}名 {self.book}"


class PriceHistory(models.Model):
    """价格历史，用于展示价格变化。"""

    book = models.ForeignKey(
        Book, verbose_name="图书", on_delete=models.CASCADE, related_name="price_history"
    )
    price = models.DecimalField("价格", max_digits=10, decimal_places=2)
    recorded_at = models.DateTimeField("记录时间", default=timezone.now)
    source = models.CharField("数据来源", max_length=32, default="dangdang")

    class Meta:
        db_table = "price_history"
        verbose_name = "价格历史"
        verbose_name_plural = "价格历史"
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["book", "-recorded_at"], name="idx_price_book_time"),
        ]

    def __str__(self):
        return f"{self.book} {self.price} ({self.recorded_at:%Y-%m-%d})"


class CrawlLog(models.Model):
    """爬虫/导入日志，记录每次采集的结果。"""

    STATUS_CHOICES = [
        ("running", "进行中"),
        ("success", "成功"),
        ("partial", "部分成功"),
        ("failed", "失败"),
    ]

    source = models.CharField("数据来源", max_length=32, default="dangdang")
    status = models.CharField(
        "状态", max_length=16, choices=STATUS_CHOICES, default="running"
    )
    records_found = models.PositiveIntegerField("发现记录数", default=0)
    records_saved = models.PositiveIntegerField("保存记录数", default=0)
    started_at = models.DateTimeField("开始时间", default=timezone.now)
    finished_at = models.DateTimeField("结束时间", null=True, blank=True)
    message = models.TextField("说明", blank=True, default="")

    class Meta:
        db_table = "crawl_log"
        verbose_name = "采集日志"
        verbose_name_plural = "采集日志"
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.started_at:%Y-%m-%d %H:%M} {self.get_status_display()}"
