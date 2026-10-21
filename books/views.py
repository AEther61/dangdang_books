from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Book, Category
from .queries import get_dashboard_data


def dashboard(request):
    """首页仪表盘：数字卡片 + 两个图表 + 最新总榜前十。"""
    context = get_dashboard_data()
    return render(request, "books/dashboard.html", context)


def book_list(request):
    """图书列表：支持搜索、分类筛选、排序和分页。"""
    keyword = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "rating")

    books = (
        Book.objects.filter(is_active=True)
        .select_related("publisher")
        .prefetch_related("authors", "categories")
    )

    if keyword:
        books = books.filter(
            Q(title__icontains=keyword)
            | Q(subtitle__icontains=keyword)
            | Q(isbn__icontains=keyword)
            | Q(authors__name__icontains=keyword)
            | Q(publisher__name__icontains=keyword)
        ).distinct()

    selected_category_id = int(category_id) if category_id.isdigit() else None
    if selected_category_id:
        books = books.filter(categories__id=selected_category_id).distinct()

    sort_map = {
        "rating": ("-rating", "-review_count", "title"),
        "price_asc": ("price", "title"),
        "price_desc": ("-price", "title"),
        "newest": ("-publish_date", "title"),
        "title": ("title",),
    }
    books = books.order_by(*sort_map.get(sort, sort_map["rating"]))

    paginator = Paginator(books, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "categories": Category.objects.order_by("name"),
        "keyword": keyword,
        "selected_category_id": selected_category_id,
        "sort": sort,
        "query_string": params.urlencode(),
    }
    return render(request, "books/book_list.html", context)


def book_detail(request, pk):
    """图书详情：基本信息、榜单记录、价格历史、同出版社推荐。"""
    book = get_object_or_404(
        Book.objects.select_related("publisher").prefetch_related(
            "authors", "categories"
        ),
        pk=pk,
        is_active=True,
    )

    rankings = (
        book.ranking_snapshots.select_related("category")
        .order_by("-snapshot_date", "rank_no")[:12]
    )
    latest_overall = (
        book.ranking_snapshots.filter(category__isnull=True)
        .order_by("-snapshot_date")
        .first()
    )
    latest_category = (
        book.ranking_snapshots.filter(category__isnull=False)
        .select_related("category")
        .order_by("-snapshot_date")
        .first()
    )

    price_history = list(book.price_history.order_by("-recorded_at")[:12])
    price_history.reverse()
    price_change = None
    if len(price_history) >= 2:
        diff = price_history[-1].price - price_history[0].price
        if diff > 0:
            price_change = {"direction": "上涨", "amount": diff}
        elif diff < 0:
            price_change = {"direction": "下降", "amount": abs(diff)}
        else:
            price_change = {"direction": "持平", "amount": diff}

    related_books = Book.objects.none()
    if book.publisher_id:
        related_books = (
            Book.objects.filter(publisher_id=book.publisher_id, is_active=True)
            .exclude(pk=book.pk)
            .select_related("publisher")
            .prefetch_related("authors")
            .order_by("-rating")[:4]
        )

    context = {
        "book": book,
        "rankings": rankings,
        "latest_overall": latest_overall,
        "latest_category": latest_category,
        "price_history": price_history,
        "price_change": price_change,
        "related_books": related_books,
    }
    return render(request, "books/book_detail.html", context)
