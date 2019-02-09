from unittest.mock import patch, call, Mock

from django.urls.base import resolve

from common.test import PacsTestCase
from reports.views import _balance_evolution_view, balance_evolution_view


class TestBalanceEvolutionReportView(PacsTestCase):

    def setUp(self):
        super().setUp()

        # Patch for BalanceEvolutionInputSerializer
        self.patcher_BalanceEvolutionInputSerializer = patch(
            'reports.views.BalanceEvolutionInputSerializer'
        )
        self.m_BalanceEvolutionInputSerializer = (
            self.patcher_BalanceEvolutionInputSerializer.start()
        )
        self.addCleanup(self.patcher_BalanceEvolutionInputSerializer.stop)

        # Patch for BalanceEvolutionOutputSerializer
        self.patcher_BalanceEvolutionOutputSerializer = patch(
            'reports.views.BalanceEvolutionOutputSerializer'
        )
        self.m_BalanceEvolutionOutputSerializer = (
            self.patcher_BalanceEvolutionOutputSerializer.start()
        )
        self.addCleanup(self.patcher_BalanceEvolutionOutputSerializer.stop)

        # Path for BalanceEvolutionQuery
        self.patcher_BalanceEvolutionQuery = patch(
            'reports.views.BalanceEvolutionQuery'
        )
        self.m_BalanceEvolutionQuery = (
            self.patcher_BalanceEvolutionQuery.start()
        )
        self.addCleanup(self.patcher_BalanceEvolutionQuery.stop)

        # Patch for Response
        self.patcher_Response = patch('reports.views.Response')
        self.m_Response = self.patcher_Response.start()
        self.addCleanup(self.patcher_Response.stop)

    def test_balance_evolution_url_resolves_to_function(self):
        assert resolve('/reports/balance-evolution/').func == balance_evolution_view

    def test_uses_BalanceEvolutionInputSerializer(self):
        # Some fake input data
        input_data = {"periods": object()}
        self.m_BalanceEvolutionInputSerializer.return_value.get_data\
            .return_value = input_data

        request = Mock()
        _balance_evolution_view(request)

        # Used the serializer
        assert self.m_BalanceEvolutionInputSerializer.call_args_list == [
            call(data=request.data)
        ]

        # Called the get_data from the serializer and passed to Query
        assert self.m_BalanceEvolutionQuery.call_args_list == [
            call(**input_data)
        ]

    def test_uses_BalanceEvolutionOutputSerializer(self):
        request = Mock()
        response = _balance_evolution_view(request)

        # Called BalanceEvolutionOutputSerializer with Query.run
        assert self.m_BalanceEvolutionOutputSerializer.call_args_list == [
            call(self.m_BalanceEvolutionQuery().run())
        ]

        # Called Response with BalanceEvolutionOutputSerializer.data
        assert self.m_Response.call_count == 1
        assert self.m_Response.call_args == call(
            self.m_BalanceEvolutionOutputSerializer().data
        )

        # Returned the response
        assert response == self.m_Response.return_value
