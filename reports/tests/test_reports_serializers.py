from copy import copy
from datetime import date
from unittest.mock import Mock, call, patch

from rest_framework.serializers import PrimaryKeyRelatedField

from accounts.tests.factories import AccountTestFactory
from common.test import PacsTestCase
from currencies.serializers import BalanceSerializer
from movements.tests.factories import TransactionTestFactory
from reports.reports import Period
from reports.serializers import (BalanceEvolutionDataSerializer,
                                 BalanceEvolutionInputSerializer,
                                 BalanceEvolutionOutputSerializer, PeriodField)

test_data = {
    "periods": [
        ["2001-01-12", "2003-01-31"],
        ["2003-02-02", "2003-02-28"]
    ],
    "accounts": [1, 2, 3]
}


class TestBalanceEvolutionInputSerializer(PacsTestCase):

    def test_integration(self):
        # Create some accounts
        self.populate_accounts()
        accs = AccountTestFactory.create_batch(3)

        # Updates data to have those accounts
        data = copy(test_data)
        data['accounts'] = [x.pk for x in accs]

        # Deserializes
        serializer = BalanceEvolutionInputSerializer(data=data)
        serializer.is_valid(True)
        validated_data = serializer.validated_data

        # Assert the periods are correct
        assert validated_data['periods'] == [
            Period(date(2001, 1, 12), date(2003, 1, 31)),
            Period(date(2003, 2, 2), date(2003, 2, 28))
        ]
        # Asserts that the accounts in balance are the ones expected
        assert validated_data['accounts'] == accs

    @patch.object(PrimaryKeyRelatedField, 'to_internal_value')
    @patch.object(PeriodField, 'to_internal_value')
    def test_serializes_accounts(
            self,
            _,
            m_to_internal_value,
    ):
        serializer = BalanceEvolutionInputSerializer(data=test_data)
        serializer.is_valid(True)
        assert m_to_internal_value.call_args_list == [
            call(x) for x in test_data['accounts']
        ]
        assert serializer.validated_data['accounts'] == \
            [m_to_internal_value()] * len(test_data['accounts'])

    @patch.object(PrimaryKeyRelatedField, 'to_internal_value')
    @patch.object(PeriodField, 'to_internal_value')
    def test_serializes_periods(self, m_to_internal_value, _):
        serializer = BalanceEvolutionInputSerializer(data=test_data)
        serializer.is_valid(True)
        assert m_to_internal_value.call_args_list == [
            call(x) for x in test_data['periods']
        ]
        assert serializer.validated_data['periods'] == [m_to_internal_value()] * 2


class TestPeriodField(PacsTestCase):

    def test_base_to_internal_value(self):
        exp = Period(date(2001, 1, 12), date(2003, 1, 31))
        res = PeriodField().to_internal_value(test_data['periods'][0])
        assert exp == res

    def test_base_to_representation(self):
        exp = ['2018-01-01', '2018-02-01']
        res = PeriodField().to_representation(
            Period(date(2018, 1, 1), date(2018, 2, 1))
        )
        assert exp == res


class TestBalanceEvolutionOutputSerializer(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.m_report = Mock()
        self.m_report.periods = [Mock(), Mock()]
        self.m_report.data = [Mock(), Mock()]

    @patch.object(PeriodField, 'to_representation')
    @patch.object(BalanceEvolutionDataSerializer, 'to_representation')
    def test_serializes_periods(self, _, m_to_representation):
        data = BalanceEvolutionOutputSerializer(self.m_report).data
        assert m_to_representation.call_args_list == [
            call(p) for p in self.m_report.periods
        ]
        assert data['periods'] == [m_to_representation()] * 2

    @patch.object(PeriodField, 'to_representation')
    @patch.object(BalanceEvolutionDataSerializer, 'to_representation')
    def test_serializes_data(self, m_to_representation, _):
        data = BalanceEvolutionOutputSerializer(self.m_report).data
        assert m_to_representation.call_args_list == [
            call(d) for d in self.m_report.data
        ]
        assert data['data'] == [m_to_representation()] * 2


@patch.object(PrimaryKeyRelatedField, 'to_representation')
@patch.object(BalanceSerializer, 'to_representation')
class TestBalanceEvolutionDataSerializer(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.data = Mock()
        self.data.balance_evolution = [Mock(), Mock()]

    def test_serializes_account(self, _, m_to_representation):
        serialized = BalanceEvolutionDataSerializer(self.data).data
        assert m_to_representation.call_count == 1
        assert serialized['account'] == m_to_representation.return_value

    def test_serializes_initial_balance_and_balance_evolution(
            self,
            m_to_representation,
            __
    ):
        serialized = BalanceEvolutionDataSerializer(self.data).data
        # Called for initial_balance
        assert m_to_representation.call_args_list[0] == call(
            self.data.initial_balance
        )
        # Called for balance_evolution
        assert m_to_representation.call_args_list[1:] == [
            call(x) for x in self.data.balance_evolution
        ]
        assert serialized['initial_balance'] == m_to_representation.return_value
        assert serialized['balance_evolution'] == 2 * [
            m_to_representation.return_value
        ]
