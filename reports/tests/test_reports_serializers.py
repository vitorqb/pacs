from copy import copy
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, call, patch, sentinel

from rest_framework.serializers import PrimaryKeyRelatedField, SlugRelatedField

from accounts.tests.factories import AccountTestFactory
from common.test import PacsTestCase
from currencies.models import Currency
from currencies.money import Money
from currencies.serializers import BalanceSerializer
from movements.tests.factories import TransactionTestFactory
from reports.reports import Period
from reports.serializers import (BalanceEvolutionDataSerializer,
                                 BalanceEvolutionInputSerializer,
                                 BalanceEvolutionOutputSerializer,
                                 CurrencyOptsSerializer,
                                 CurrencyPricePortifolioSerializer,
                                 FlowEvolutionInputSerializer,
                                 FlowEvolutionOutputSerializer, PeriodField)

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


class TestCurrencyOptsSerializer(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.populate_currencies()

    @staticmethod
    def get_data(**kwargs):
        out = {
            'price_portifolio': [
                {
                    'currency': 'EUR',
                    'prices': [
                        {'date': '2019-01-01', 'price': 1},
                        {'date': '2019-01-15', 'price': 2},
                        {'date': '2019-01-25', 'price': 3},
                    ],
                },
                {
                    'currency': 'BRL',
                    'prices': [
                        {'date': '2019-01-01', 'price': 0.25},
                        {'date': '2019-01-15', 'price': 0.5},
                        {'date': '2019-01-20', 'price': 1},
                    ],
                },
            ],
            'convert_to': 'BRL'
        }
        out.update(**kwargs)
        return out

    def test_base(self):
        euro = Currency.objects.get(code='EUR')
        real = Currency.objects.get(code='BRL')
        data = self.get_data()
        serializer = CurrencyOptsSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data == {
            'price_portifolio': [
                {
                    'currency': euro,
                    'prices': [
                        {'date': date(2019, 1, 1), 'price': Decimal(1)},
                        {'date': date(2019, 1, 15), 'price': Decimal(2)},
                        {'date': date(2019, 1, 25), 'price': Decimal(3)},
                    ]
                },
                {
                    'currency': real,
                    'prices': [
                        {'date': date(2019, 1, 1), 'price': Decimal('0.25')},
                        {'date': date(2019, 1, 15), 'price': Decimal('0.5')},
                        {'date': date(2019, 1, 20), 'price': Decimal('1')},
                    ]
                }
            ],
            'convert_to': real,
        }


class TestFlowEvolutionInputSerializer:

    @staticmethod
    def patch_get_queryset():
        # Needed because of reflection in rest_framework.serializers
        new = Mock(__func__=None)
        return patch.object(PrimaryKeyRelatedField, 'get_queryset', new)

    @staticmethod
    def get_data(**kwargs):
        out = {
            'periods': [
                [
                    '2019-01-01',
                    '2019-01-31',
                ],
                [
                    '2019-02-01',
                    '2019-02-28',
                ]
            ],
            'accounts': [
                12,
                24,
            ]
        }
        out.update(**kwargs)
        return out

    def test_base(self):
        data = self.get_data()
        serializer = FlowEvolutionInputSerializer(data=data)
        with self.patch_get_queryset() as get_queryset:
            serializer.is_valid(True)
            resp = serializer.validated_data
        assert resp['periods'] == [
            PeriodField().to_internal_value(x) for x in data['periods']
        ]
        assert get_queryset().get.call_args_list == [call(pk=12), call(pk=24)]
        assert resp['accounts'] == [get_queryset().get(), get_queryset().get()]

    def test_empty_list_for_periods_raises_err(self):
        data = self.get_data(periods=[])
        serializer = FlowEvolutionInputSerializer(data=data)
        with self.patch_get_queryset():
            assert serializer.is_valid() is False
        assert 'periods' in serializer.errors


class TestFlowEvolutionOutputSerializer(PacsTestCase):

    @staticmethod
    def get_data(**kwargs):
        currency = Mock(pk=1)
        out = [
            {
                'account': Mock(pk=1),
                'flows': [
                    {
                        'period': Period(date(2019, 1, 1), date(2019, 1, 31)),
                        'moneys': [Money(currency=currency, quantity=2)]
                    }
                ]
            }
        ]
        return out

    def test_base(self):
        data = self.get_data()
        serializer = FlowEvolutionOutputSerializer(data)
        assert dict(serializer.data) == {
            'data': [
                {
                    'account': 1,
                    'flows': [
                        {
                            'period': ['2019-01-01', '2019-01-31'],
                            'moneys': [
                                {
                                    'currency': 1,
                                    'quantity': '2.00000'
                                }
                            ]
                        }
                    ]
                }
            ]
        }


class TestCurrencyPricePortifolioSerializer:

    @staticmethod
    def get_data():
        return {
            'currency': 'EUR',
            'prices': [
                {'date': '2019-01-01', 'price': 12}
            ]
        }

    @staticmethod
    def patch_get_queryset():
        # Needed because of reflection in rest_framework.serializers
        new = Mock(__func__=None)
        return patch.object(SlugRelatedField, 'get_queryset', new=new)

    def test_base(self):
        data = self.get_data()
        with self.patch_get_queryset() as get_queryset:
            serializer = CurrencyPricePortifolioSerializer(data=data)
            assert serializer.is_valid(), serializer.errors
            validated_data = serializer.validated_data
        assert get_queryset().get.call_args_list == [call(code='EUR')]
        assert validated_data == {
            'currency': get_queryset().get(code='EUR'),
            'prices': [
                {'date': date(2019, 1, 1), 'price': Decimal(12)}
            ]
        }
