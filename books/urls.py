from django.urls import path

from . import views

app_name = "books"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("books/", views.book_list, name="book_list"),
    path("books/<int:pk>/", views.book_detail, name="book_detail"),
]
