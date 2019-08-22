from datetime import date
from decimal import Decimal
from unittest.mock import Mock, call, patch, sentinel

from django.urls.base import resolve

import common.utils as utils
from accounts.tests.factories import AccountTestFactory
from common.test import PacsTestCase
from currencies.currency_converter import (UnkownCurrencyForConversion,
                                           UnkownDateForCurrencyConversion)
from currencies.models import Currency
from currencies.money import Balance, Money
from currencies.tests.factories import CurrencyTestFactory
from movements.tests.factories import TransactionTestFactory
from reports.reports import BalanceEvolutionReport, BalanceEvolutionReportData
from reports.serializers import BalanceEvolutionOutputSerializer
from reports.view_models import BalanceEvolutionInput
from reports.views import (BalanceEvolutionViewSpec, FlowEvolutionViewSpec,
                           balance_evolution_view)


class TestBalanceEvolutionViewUrl:

    def test_url_resolves(self):
        func = resolve('/reports/balance-evolution/').func
        assert func == balance_evolution_view


class TestBalanceEvolutionViewSpecSerializeInputs(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.populate_accounts()

    def test_base(self):
        accounts = AccountTestFactory.create_batch(2)
        dates = [date(2019, 1, 1), date(2019, 2, 1)]
        raw = {
            "accounts": [x.pk for x in accounts],
            "dates": [utils.date_to_str(d) for d in dates],
        }
        request = Mock(data=raw)
        deserialized = BalanceEvolutionViewSpec._serialize_inputs(request)
        assert deserialized == BalanceEvolutionInput(accounts, dates)


class TestBalanceEvolutionViewSpecPost(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.populate_accounts()
        self.populate_currencies()

    def test_base(self):
        # Creates and returns a dummy BalanceEvolutionReport
        dates = [date(2019, 1, 1), date(2020, 1, 1)]
        account = AccountTestFactory()
        transaction1 = TransactionTestFactory(
            movements_specs__0__account=account,
            date_=dates[0],
        )
        balance1 = transaction1.get_balance_for_account(account)
        transaction2 = TransactionTestFactory(
            movements_specs__0__account=account,
            date_=dates[1],
        )
        balance2 = balance1 + transaction2.get_balance_for_account(account)
        data = {
            "dates": [utils.date_to_str(d) for d in dates],
            "accounts": [account.pk],
        }
        request = Mock(data=data)

        exp_report_data = [
            BalanceEvolutionReportData(
                date=dates[0],
                account=account,
                balance=balance1,
            ),
            BalanceEvolutionReportData(
                date=dates[1],
                account=account,
                balance=balance2,
            )
        ]
        exp_report = BalanceEvolutionReport(exp_report_data)
        serialized_exp_report = BalanceEvolutionOutputSerializer(exp_report).data
        with patch('reports.views.Response') as Response:
            result = BalanceEvolutionViewSpec.post(request)
        assert Response.call_args_list == [call(serialized_exp_report)]
        assert result == Response()

    def test_with_currency_opts(self):
        currency_from = Currency.objects.get(code='EUR')
        currency_to = Currency.objects.get(code="BRL")

        date_ = date(2018, 1, 1)
        account = AccountTestFactory()
        money = Money(Decimal('2'), currency_from)
        transaction = TransactionTestFactory(
            movements_specs__0__money=money,
            movements_specs__0__account=account,
            date_=date_,
        )

        data = {
            "dates": [utils.date_to_str(date_)],
            "accounts": [account.pk],
            "currency_opts": {
                "price_portifolio": [
                    {
                        "currency": currency_from.get_code(),
                        "prices": [{"date": utils.date_to_str(date_), "price": 1}]
                    },
                    {
                        "currency": currency_to.get_code(),
                        "prices": [{"date": utils.date_to_str(date_), "price": 1/5}]
                    }
                ],
                "convert_to": currency_to.get_code(),
            }
        }
        request = Mock(data=data)

        exp_balance_report_data = [BalanceEvolutionReportData(
            date=date_,
            account=account,
            balance=Balance([Money(Decimal('10'), currency_to)]),
        )]
        exp_report = BalanceEvolutionReport(exp_balance_report_data)
        exp_serialized = BalanceEvolutionOutputSerializer(exp_report).data
        with patch('reports.views.Response') as Response:
            result = BalanceEvolutionViewSpec.post(request)
        assert Response.call_args_list == [call(exp_serialized)]
        assert result == Response()


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


class TestFlowEvolutionView(PacsTestCase):

    endpoint = '/reports/flow-evolution/'

    def test_returns_400_if_unkown_currency(self):
        msg = 'Foo Bar'
        with patch(
                'reports.views.FlowEvolutionViewSpec._serialize_inputs',
                side_effect=UnkownCurrencyForConversion(msg),
        ):
            resp = self.client.post(self.endpoint, {})
        assert resp.status_code == UnkownCurrencyForConversion.status_code
        assert resp.json() == {'detail': msg}

    def test_return_400_if_unkown_date(self):
        msg = 'Foo Bar Baz'
        with patch(
                'reports.views.FlowEvolutionViewSpec._serialize_inputs',
                side_effect=UnkownDateForCurrencyConversion(msg)
        ):
            resp = self.client.post(self.endpoint, {})
        assert resp.status_code == UnkownDateForCurrencyConversion.status_code
        assert resp.json() == {'detail': msg}
