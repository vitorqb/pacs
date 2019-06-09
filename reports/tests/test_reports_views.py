from unittest.mock import Mock, call, patch, sentinel

from django.urls.base import resolve

from common.test import PacsTestCase
from reports.views import (FlowEvolutionViewSpec, _balance_evolution_view,
                           balance_evolution_view)


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


class TestFlowEvolutionViewSpecPost:

    @staticmethod
    def patch_serialize_inptus():
        return patch.object(FlowEvolutionViewSpec, '_serialize_inputs')

    @staticmethod
    def patch_run_query():
        return patch.object(FlowEvolutionViewSpec, '_run_query')

    @staticmethod
    def patch_serializer_report():
        return patch.object(FlowEvolutionViewSpec, '_serialize_report')

    @staticmethod
    def patch_response():
        return patch('reports.views.Response')

    def run(self):
        with self.patch_serialize_inptus() as _serialize_inputs,\
             self.patch_run_query() as _run_query,\
             self.patch_serializer_report() as _serialize_report,\
             self.patch_response() as Response:

            self.resp = FlowEvolutionViewSpec.post(sentinel.request)

        self._serialize_inputs = _serialize_inputs
        self._run_query = _run_query
        self._serialize_report = _serialize_report
        self.Response = Response

    def test_calls_serialize_inputs(self):
        self.run()
        assert self._serialize_inputs.call_args_list == [call(sentinel.request)]

    def test_calls_run_query(self):
        self.run()
        assert self._run_query.call_args_list == [call(self._serialize_inputs())]

    def test_calls_serialize_report(self):
        self.run()
        assert self._serialize_report.call_args_list == [call(self._run_query())]

    def test_returns_response(self):
        self.run()
        assert self.Response.call_args_list == [call(self._serialize_report())]
        assert self.resp == self.Response()


class TestFlowEvolutionViewSpecSerializeInputs:

    @staticmethod
    def patch_serializer():
        return patch('reports.views.FlowEvolutionInputSerializer', autospec=True)

    def test_calls_serializers_with_request_daya(self):
        request = Mock()
        with self.patch_serializer() as Serializer:
            FlowEvolutionViewSpec._serialize_inputs(request)
        assert Serializer.call_args_list == [call(data=request.data)]

    def test_calls_is_valid(self):
        with self.patch_serializer() as Serializer:
            FlowEvolutionViewSpec._serialize_inputs(Mock())
        assert Serializer().is_valid.call_args_list == [call(True)]

    def test_returns_serializer_create(self):
        with self.patch_serializer() as Serializer:
            response = FlowEvolutionViewSpec._serialize_inputs(Mock())
        serializer = Serializer()
        assert serializer.save.call_args_list == [call()]
        assert response == serializer.save()


class TestFlowEvolutionViewSpecRunQuery:

    @staticmethod
    def patch_flow_evolution_query():
        return patch('reports.views.FlowEvolutionQuery', autospec=True)

    @staticmethod
    def patch_get_converter_fn():
        return patch('reports.views.FlowEvolutionViewSpec._get_converter_fn')

    def test_calls_query_run_method(self):
        class Inputs:
            accounts = sentinel.accounts
            periods = sentinel.periods
            currency_opts = sentinel.currency_opts

        inputs = Inputs()
        with self.patch_flow_evolution_query() as FlowEvolutionQuery:
            with self.patch_get_converter_fn() as get_converter_fn:
                response = FlowEvolutionViewSpec._run_query(inputs)
        assert FlowEvolutionQuery.call_args_list == [call(
            accounts=Inputs.accounts,
            periods=Inputs.periods,
            currency_conversion_fn=get_converter_fn()
        )]
        assert FlowEvolutionQuery.return_value.run.call_args_list == [call()]
        assert response == FlowEvolutionQuery.return_value.run()


class TestFlowEvolutionSerializeReport:

    @staticmethod
    def patch_serializer():
        return patch('reports.views.FlowEvolutionOutputSerializer', autospec=True)

    def test_calls_serializer_with_report(self):
        report = Mock()
        with self.patch_serializer() as Serializer:
            result = FlowEvolutionViewSpec._serialize_report(report)
        serializer = Serializer.return_value
        assert Serializer.call_args_list == [call(report)]
        assert result == serializer.data
