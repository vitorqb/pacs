from common.test import PacsTestCase
import datetime
from rest_framework.test import APIRequestFactory
import exchangerates.views as sut


class GetExchangeRateDataTest(PacsTestCase):

    def test_returns_200_with_exchange_rates_from_service(self):

        mock_data = [
            {
                "currency": "EUR",
                "prices": [
                    {"date": "2020-01-01", "price": 0.8},
                    {"date": "2020-01-02", "price": 0.85},
                ]
            },
            {
                "currency": "BRL",
                "prices": [
                    {"date": "2020-01-01", "price": 4},
                    {"date": "2020-01-02", "price": 4.2},
                ]
            }
        ]

        def mock_fetch_exchange_rates(start_at, end_at, currency_codes):
            assert start_at == datetime.date(2020, 1, 1)
            assert end_at == datetime.date(2020, 1, 2)
            assert currency_codes == ["EUR", "BRL"]
            return mock_data

        params = {
            "start_at": "2020-01-01",
            "end_at": "2020-01-02",
            "currency_codes": "EUR,BRL",
        }
        request = APIRequestFactory().get("/exchange_rate/data/v2", params)
        result = sut.get_exchangerates(request, fetch_fn=mock_fetch_exchange_rates)
        assert result.status_code == 200
        assert result.data == mock_data
