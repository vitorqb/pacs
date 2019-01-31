import attr
from rest_framework import pagination


# !!!! TODO -> Remove (has same effect as usual PageNumberPagination)
@attr.s()
class OptionalPageNumberPaginator():
    """ A wrapper around PageNumberPagination that only paginates if
    the query_param is parsed. """

    # A paginator being wrapped
    _paginator: pagination.BasePagination = attr.ib()

    def paginate_queryset(self, queryset, request, view=None):
        if self._paginator.page_query_param not in request.query_params:
            return None
        return self._paginator.paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        return self._paginator.get_paginated_response(data)

    def to_html(self):
        return self._paginator.to_html()

    def get_results(self, data):
        return self._paginator.get_results(data)
