from rest_framework.pagination import CursorPagination


class BidCursorPagination(CursorPagination):
    ordering = ("-created_at", "-id")
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 100
