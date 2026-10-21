from django.contrib import admin

from .models import (
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


class BookAuthorInline(admin.TabularInline):
    model = BookAuthor
    extra = 0
    autocomplete_fields = ["author"]


class BookCategoryInline(admin.TabularInline):
    model = BookCategory
    extra = 0
    autocomplete_fields = ["category"]


class RankingSnapshotInline(admin.TabularInline):
    model = RankingSnapshot
    extra = 0
    fields = ["category", "rank_no", "snapshot_date"]
    ordering = ["-snapshot_date", "rank_no"]


class PriceHistoryInline(admin.TabularInline):
    model = PriceHistory
    extra = 0
    fields = ["price", "recorded_at", "source"]
    ordering = ["-recorded_at"]


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ["name", "website", "created_at"]
    search_fields = ["name"]


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    search_fields = ["name"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "isbn",
        "publisher",
        "price",
        "rating",
        "review_count",
        "publish_date",
        "is_active",
    ]
    list_filter = ["publisher", "categories", "is_active"]
    search_fields = ["title", "subtitle", "isbn", "authors__name", "publisher__name"]
    list_select_related = ["publisher"]
    date_hierarchy = "publish_date"
    inlines = [
        BookAuthorInline,
        BookCategoryInline,
        RankingSnapshotInline,
        PriceHistoryInline,
    ]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "created_at"]
    list_filter = ["parent"]
    search_fields = ["name"]


@admin.register(BookAuthor)
class BookAuthorAdmin(admin.ModelAdmin):
    list_display = ["book", "author", "author_order"]
    search_fields = ["book__title", "author__name"]
    autocomplete_fields = ["book", "author"]


@admin.register(BookCategory)
class BookCategoryAdmin(admin.ModelAdmin):
    list_display = ["book", "category", "is_primary"]
    list_filter = ["category", "is_primary"]
    search_fields = ["book__title", "category__name"]
    autocomplete_fields = ["book", "category"]


@admin.register(RankingSnapshot)
class RankingSnapshotAdmin(admin.ModelAdmin):
    list_display = ["book", "category", "rank_no", "snapshot_date"]
    list_filter = ["category", "snapshot_date"]
    search_fields = ["book__title"]
    date_hierarchy = "snapshot_date"
    autocomplete_fields = ["book", "category"]


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ["book", "price", "recorded_at", "source"]
    list_filter = ["source"]
    search_fields = ["book__title"]
    date_hierarchy = "recorded_at"
    autocomplete_fields = ["book"]


@admin.register(CrawlLog)
class CrawlLogAdmin(admin.ModelAdmin):
    list_display = [
        "started_at",
        "source",
        "status",
        "records_found",
        "records_saved",
        "finished_at",
    ]
    list_filter = ["status", "source"]
    search_fields = ["message"]
    date_hierarchy = "started_at"
