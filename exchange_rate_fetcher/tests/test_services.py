from unittest import TestCase
from unittest.mock import patch, call
import exchange_rate_fetcher.services as sut
import pytest
from datetime import date


class ExchangeRateFetcherTest(TestCase):

    def test__fetch__base_integration(self):
        raw_data = {
            "rates": {
                "2020-01-03": {"EUR": 1, "BRL": 4},
                "2020-01-02": {"EUR": 1, "BRL": 4},
                "2020-01-06": {"EUR": 1, "BRL": 4.1}
            }
        }
        start_at = "2019-01-01"
        end_at = "2020-01-01"
        symbols = ["EUR", "BRL"]
        base = "USD"
        params = {"start_at": start_at,
                  "end_at": end_at,
                  "symbols": sut.ExchangeRateFetcher
                  ._list_to_comma_separated_string(symbols),
                  "base": base}
        date_fmt = sut.ExchangeRateFetcher._DATE_FORMAT
        service_url = sut.ExchangeRateFetcher._THIRD_PARTY_SERVICE_URL

        with patch.object(sut.ExchangeRateFetcher, '_do_fetch_data')\
                as m_do_fetch_data:
            m_do_fetch_data.return_value = raw_data
            result = sut.ExchangeRateFetcher().fetch(start_at, end_at, symbols,
                                                     base)

        assert m_do_fetch_data.call_count == 1
        assert m_do_fetch_data.call_args == call(service_url, params)
        assert result == sut.ExchangeRateDataTranslator()\
                            .translate_raw_data(raw_data, date_fmt)

    def test__do_fetch_data__calls_requests_get(self):
        url = "http://foo.com"
        params = {"bar": 1}
        with patch("exchange_rate_fetcher.services.requests") as m_requests:
            sut.ExchangeRateFetcher._do_fetch_data(url, params)
        assert m_requests.get.call_count == 1
        assert m_requests.get.call_args == call(url, params=params)

    def test__do_fetch_data__calls_raise_for_status(self):
        with patch("exchange_rate_fetcher.services.requests") as m_requests:
            sut.ExchangeRateFetcher._do_fetch_data("", {})
        assert m_requests.get().raise_for_status.call_count == 1

    def test__list_to_comma_separated_string(self):
        lst = ["A", "B"]
        exp = "A,B"
        assert sut.ExchangeRateFetcher._list_to_comma_separated_string(lst)\
            == exp

    def test__date_to_str__with_str_input(self):
        assert sut.ExchangeRateFetcher._date_to_str("2019-01-01", "%Y-%m-%d")\
            == "2019-01-01"

    def test__date_to_str__with_none(self):
        assert sut.ExchangeRateFetcher._date_to_str(None, "%Y-%m-%d", True)\
            is None

    def test__date_to_str__error_with_none(self):
        with pytest.raises(AttributeError):
            sut.ExchangeRateFetcher._date_to_str(None, "%Y")

    def test__date_to_str__datetime(self):
        date_ = date(2019, 1, 1)
        assert sut.ExchangeRateFetcher._date_to_str(date_, "%Y") == "2019"


class ExchangeRateDataTranslatorTest(TestCase):

    @staticmethod
    def _sort_by_date(x):
        return sorted(x, key=lambda x: x['date'])

    def _compare_result(self, exp, res):
        exp_currencies = set(x["currency"] for x in exp)
        res_currencies = set(x["currency"] for x in res)
        assert exp_currencies == res_currencies

        for cur in exp_currencies:
            exp_prices = next(x for x in exp if x["currency"] == cur)['prices']
            res_prices = next(x for x in res if x["currency"] == cur)['prices']
            assert self._sort_by_date(exp_prices) == self._sort_by_date(res_prices)

        return True

    def test__translate_raw_data(self):
        max_date = "2020-01-07"
        date_fmt = "%Y-%m-%d"
        raw_data = {
            "rates": {
                "2020-01-03": {"EUR": 1, "BRL": 4},
                "2020-01-02": {"EUR": 1, "BRL": 4},
                "2020-01-06": {"EUR": 1, "BRL": 4.2}
            }
        }
        exp_data = [
            {"currency": "EUR",
             "prices": [
                 {"date": "2020-01-02", "price": 1.0},
                 {"date": "2020-01-03", "price": 1.0},
                 {"date": "2020-01-04", "price": 1.0},
                 {"date": "2020-01-05", "price": 1.0},
                 {"date": "2020-01-06", "price": 1.0},
                 {"date": "2020-01-07", "price": 1.0}
             ]},
            {"currency": "BRL",
             "prices": [
                 {"date": "2020-01-02", "price": 1/4},
                 {"date": "2020-01-03", "price": 1/4},
                 {"date": "2020-01-04", "price": 1/4},
                 {"date": "2020-01-05", "price": 1/4},
                 {"date": "2020-01-06", "price": 1/4.2},
                 {"date": "2020-01-07", "price": 1/4.2}
             ]}
        ]
        translator = sut.ExchangeRateDataTranslator()
        result = translator.translate_raw_data(raw_data, date_fmt, max_date)
        self._compare_result(exp_data, result)
