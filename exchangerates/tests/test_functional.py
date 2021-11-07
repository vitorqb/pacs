import exchangerates.models as models
import pytest
import datetime
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from common.test import TestRequests
import tempfile
from contextlib import contextmanager
import exchangerates.views as views


test_data = (
    ("EUR", datetime.date(2020, 1, 1), 0.8),
    ("EUR", datetime.date(2020, 1, 2), 0.85),
    ("BRL", datetime.date(2020, 1, 1), 4),
    ("BRL", datetime.date(2020, 1, 2), 4.2),
)


@contextmanager
def temp_csv():
    with tempfile.NamedTemporaryFile() as f:
        f.writelines([
            b'date,currency_code,value',
            b'\n2021-10-15,EUR,1.1600',
            b'\n2021-10-14,EUR,1.1594',
            b'\n2021-10-15,BRL,0.1831',
            b'\n2021-10-14,BRL,0.1813',
        ])
        f.flush()
        f.seek(0)
        yield f


def new_params(**opts):
    return {
        "start_at": "2020-01-01",
        "end_at": "2020-01-03",
        "currency_codes": "EUR,BRL",
        **opts
    }


def save_test_data():
    for (c, d, v) in test_data:
        models.ExchangeRate.objects.create(currency_code=c, date=d, value=v)


@pytest.mark.functional
class ExchangeRatesFunctionalTests(StaticLiveServerTestCase):

    def run_get_request(self, params):
        return TestRequests(self.live_server_url).get("/exchange_rates/data/v2", params)

    def run_post_request(self, exchangerates_csv=None, params=None):
        files = {}
        if exchangerates_csv is not None:
            files[views.POST_CSV_FILE_NAME] = exchangerates_csv
        request = TestRequests(self.live_server_url)
        return request.post("/exchange_rates/data/v2", files=files, params=params)

    def test_get_exchange_rates(self):
        save_test_data()
        result = self.run_get_request(new_params())
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
        result = self.run_get_request(new_params())
        assert result.status_code == 400
        assert result.json() == {'detail': 'Missing data for EUR 2020-01-01'}

    def test_post_and_get_exchange_rates(self):
        with temp_csv() as exchangerates_csv:
            result = self.run_post_request(exchangerates_csv)
        assert result.status_code == 200
        get_params = new_params(start_at="2021-10-14", end_at="2021-10-15")
        get_result = self.run_get_request(get_params)
        assert get_result.status_code == 200
        assert get_result.json() == [
            {
                "currency": "EUR",
                "prices": [
                    {"date": "2021-10-14", "price": 1.1594},
                    {"date": "2021-10-15", "price": 1.16},
                ]
            },
            {
                "currency": "BRL",
                "prices": [
                    {"date": "2021-10-14", "price": 0.1813},
                    {"date": "2021-10-15", "price": 0.1831},
                ]
            }
        ]

    def test_post_existing_exchange_rates_fails(self):
        with temp_csv() as exchangerates_csv:
            result_1 = self.run_post_request(exchangerates_csv)
            exchangerates_csv.seek(0)
            result_2 = self.run_post_request(exchangerates_csv)
        assert result_1.status_code == 200
        assert result_2.status_code == 400
        assert result_2.json() == {
            'detail': ('Exchange rate already exists for '
                       'ExchangeRateImportInput(currency_code=\'EUR\', date_str=\'2021-10-15\''
                       ', value_float=\'1.1600\')')
        }

    def test_post_existing_with_skip_option_works(self):
        params = {"skip_existing": 'true'}
        with temp_csv() as exchangerates_csv:
            result_1 = self.run_post_request(exchangerates_csv, params)
            exchangerates_csv.seek(0)
            result_2 = self.run_post_request(exchangerates_csv, params)
        assert result_1.status_code == 200
        assert result_2.status_code == 200
