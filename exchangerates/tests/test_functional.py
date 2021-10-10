import exchangerates.models as models
import pytest
import datetime
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from common.test import TestRequests


test_data = (
    ("EUR", datetime.date(2020, 1, 1), 0.8),
    ("EUR", datetime.date(2020, 1, 2), 0.85),
    ("BRL", datetime.date(2020, 1, 1), 4),
    ("BRL", datetime.date(2020, 1, 2), 4.2),
)


def new_params():
    return {
        "start_at": "2020-01-01",
        "end_at": "2020-01-03",
        "currency_codes": "EUR,BRL",
    }


def save_test_data():
    for (c, d, v) in test_data:
        models.ExchangeRate.objects.create(currency_code=c, date=d, value=v)


@pytest.mark.functional
class ExchangeRatesFunctionalTests(StaticLiveServerTestCase):

    def run_request(self, params):
        return TestRequests(self.live_server_url).get("/exchange_rates/data/v2", params)

    def test_get_exchange_rates(self):
        save_test_data()
        result = self.run_request(new_params())
        assert result.status_code == 200
        assert result.json() == [
            {
                "currency": "EUR",
                "prices": [
                    {"date": "2020-01-01", "price": 0.8},
                    {"date": "2020-01-02", "price": 0.85},
                    {"date": "2020-01-03", "price": 0.85},
                ]
            },
            {
                "currency": "BRL",
                "prices": [
                    {"date": "2020-01-01", "price": 4},
                    {"date": "2020-01-02", "price": 4.2},
                    {"date": "2020-01-03", "price": 4.2},
                ]
            }
        ]

    def test_get_with_missing_data(self):
        result = self.run_request(new_params())
        assert result.status_code == 400
        assert result.json() == {'detail': 'Missing data for date: 2019-12-31'}
