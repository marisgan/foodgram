from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class PageNumberLimitPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 100
