from common.test import PacsTestCase
import datetime
import exchangerates.services as sut
import exchangerates.models as models
import exchangerates.exceptions as exceptions
from decimal import Decimal
import pytest


test_data = (
    ("EUR", datetime.date(2020, 1, 1), Decimal("0.8")),
    ("EUR", datetime.date(2020, 1, 2), Decimal("0.85")),
    ("EUR", datetime.date(2020, 1, 5), Decimal("0.90")),
    ("BRL", datetime.date(2020, 1, 1), Decimal("4")),
    ("BRL", datetime.date(2020, 1, 2), Decimal("4.2")),
    ("BRL", datetime.date(2020, 1, 5), Decimal("4.25")),
)


def create_test_data():
    for (c, d, v) in test_data:
        models.ExchangeRate.objects.create(currency_code=c, date=d, value=v)


class TestFetchExchangeRates(PacsTestCase):

    def test_fills_gaps_with_previous_date(self):
        create_test_data()
        result = sut.fetch_exchange_rates(
            datetime.date(2020, 1, 1),
            datetime.date(2020, 1, 6),
            currency_codes=["EUR", "BRL"]
        )
        exp_result = [
            {
                "currency": "EUR",
                "prices": [
                    {"date": "2020-01-01", "price": 0.8},
                    {"date": "2020-01-02", "price": 0.85},
                    {"date": "2020-01-03", "price": 0.85},
                    {"date": "2020-01-04", "price": 0.85},
                    {"date": "2020-01-05", "price": 0.90},
                    {"date": "2020-01-06", "price": 0.90},
                ]
            },
            {
                "currency": "BRL",
                "prices": [
                    {"date": "2020-01-01", "price": 4.0},
                    {"date": "2020-01-02", "price": 4.2},
                    {"date": "2020-01-03", "price": 4.2},
                    {"date": "2020-01-04", "price": 4.2},
                    {"date": "2020-01-05", "price": 4.25},
                    {"date": "2020-01-06", "price": 4.25},
                ]
            }
        ]
        assert result == exp_result

    def test_throws_when_no_info_for_start_at(self):
        create_test_data()
        with pytest.raises(exceptions.NotEnoughData):
            sut.fetch_exchange_rates(
                datetime.date(2019, 1, 1),
                datetime.date(2020, 1, 1),
                currency_codes=["EUR", "BRL"]
            )
