from unittest.mock import Mock, call

from common.pagination import OptionalPageNumberPaginator
from common.testutils import PacsTestCase


class TestOptionalPageNumberPaginator(PacsTestCase):
    def test_get_paginated_response_delegates(self):
        underlying_pag = Mock()
        args = (Mock(),)
        pag = OptionalPageNumberPaginator(underlying_pag)
        assert (
            pag.get_paginated_response(*args) == underlying_pag.get_paginated_response.return_value
        )
        underlying_pag.get_paginated_response.assert_called_with(*args)

    def test_get_to_html_delegates(self):
        underlying_pag = Mock()
        pag = OptionalPageNumberPaginator(underlying_pag)
        assert pag.to_html() == underlying_pag.to_html.return_value
        underlying_pag.to_html.assert_called_with()

    def test_get_results_delegates(self):
        underlying_pag = Mock()
        pag = OptionalPageNumberPaginator(underlying_pag)
        args = (Mock(),)
        assert pag.get_results(*args) == underlying_pag.get_results.return_value
        underlying_pag.get_results.assert_called_with(*args)

    def test_paginate_queryset_delegates_if_page(self):
        underlying_pag = Mock()
        underlying_pag.page_query_param = "paggge"
        pag = OptionalPageNumberPaginator(underlying_pag)

        request = Mock()
        request.query_params = {"paggge": 12}
        args = (Mock(), request, Mock())

        assert pag.paginate_queryset(*args) == underlying_pag.paginate_queryset.return_value
        underlying_pag.paginate_queryset.assert_called_with(*args)
