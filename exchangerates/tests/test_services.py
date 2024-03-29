import datetime
from decimal import Decimal

import django.db.utils
import pytest

import exchangerates.exceptions as exceptions
import exchangerates.models as models
import exchangerates.services as sut
from common.testutils import PacsTestCase

test_data = (
    ("EUR", datetime.date(2020, 1, 1), Decimal("0.8")),
    ("EUR", datetime.date(2020, 1, 2), Decimal("0.85")),
    ("EUR", datetime.date(2020, 1, 5), Decimal("0.90")),
    ("BRL", datetime.date(2020, 1, 1), Decimal("4")),
    ("BRL", datetime.date(2020, 1, 2), Decimal("4.2")),
    ("BRL", datetime.date(2020, 1, 5), Decimal("4.25")),
)

exchangerate_import_input = sut.ExchangeRateImportInput("EUR", "2020-01-01", 1.1)


def create_test_data():
    for (c, d, v) in test_data:
        models.ExchangeRate.objects.create(currency_code=c, date=d, value=v)


class TestFetchExchangeRates(PacsTestCase):
    def test_fills_gaps_with_previous_date(self):
        create_test_data()
        result = sut.fetch_exchange_rates(
            datetime.date(2020, 1, 1), datetime.date(2020, 1, 6), currency_codes=["EUR", "BRL"]
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
                ],
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
                ],
            },
        ]
        assert result == exp_result

    def test_throws_when_no_info_for_start_at(self):
        create_test_data()
        with pytest.raises(exceptions.NotEnoughData):
            sut.fetch_exchange_rates(
                datetime.date(2019, 1, 1), datetime.date(2020, 1, 1), currency_codes=["EUR", "BRL"]
            )


class TestImportExchangerate(PacsTestCase):
    def test_import_one(self):
        assert models.ExchangeRate.objects.all().count() == 0

        sut.import_exchangerate(exchangerate_import_input)

        assert models.ExchangeRate.objects.all().count() == 1
        model = sut.models.ExchangeRate.objects.all().first()
        assert model.currency_code == "EUR"
        assert model.date == datetime.date(2020, 1, 1)
        assert model.value == Decimal("1.1")

    def test_import_twice_failes(self):
        sut.import_exchangerate(exchangerate_import_input)
        with pytest.raises(django.db.utils.IntegrityError):
            sut.import_exchangerate(exchangerate_import_input)

    def test_import_twice_works_if_ignore_existing(self):
        options = sut.ExchangeRateImportOptions(skip_existing=True)
        sut.import_exchangerates([exchangerate_import_input], options)
        sut.import_exchangerates([exchangerate_import_input], options)
