import attr
import requests
import common.utils as utils
from datetime import datetime, timedelta
from django.conf import settings


@attr.s()
class ExchangeRateFetcher:
    """ Service to fetch exchange rates. """

    token = attr.ib(default=None)

    def fetch(self, start_at, end_at, symbols, base, max_date=None):
        translator = ExchangeRateDataTranslator()
        third_party_fetcher = _get_third_party_fetcher()
        start_at = self._date_to_str(start_at, utils.DATE_FORMAT)
        end_at = self._date_to_str(end_at, utils.DATE_FORMAT)
        max_date = self._date_to_str(max_date, utils.DATE_FORMAT, True)
        symbols = self._list_to_comma_separated_string(symbols)
        params = {"start_at": start_at,
                  "end_at": end_at,
                  "symbols": symbols,
                  "base": base}
        if self.token:
            params["access_key"] = self.token
        raw_data = third_party_fetcher.run(params)
        return translator.translate_raw_data(raw_data, utils.DATE_FORMAT,
                                             max_date)

    @staticmethod
    def _list_to_comma_separated_string(lst):
        return ",".join(lst)

    @staticmethod
    def _date_to_str(x, fmt, allow_none=False):
        """ Parses a date to string, if it is not already a string """
        if (x is None and allow_none is True) or isinstance(x, str):
            return x
        return x.strftime(fmt)


# Third Party Fetchers
def _get_third_party_fetcher():
    """ Initializes the implementation for the third party fetcher """
    if settings.TEST is True:
        return MockedThirdPartyFetcher()
    return ThirdPartyFetcher()


class ThirdPartyFetcher:
    """
    Real implementation to fetch data from the third party exchange
    rate service
    """

    _URL = 'https://api.exchangeratesapi.io/v1/timeseries'
    _requests = requests

    @classmethod
    def run(cls, params):
        out = cls._requests.get(cls._URL, params=params)
        out.raise_for_status()
        return out.json()


class MockedThirdPartyFetcher:
    """
    Mocked implementation for testing
    """

    def run(self, params):
        return {
            "rates": {
                "2020-01-02": {"EUR": 1, "BRL": 4},
                "2020-01-03": {"EUR": 1, "BRL": 4},
                "2020-01-06": {"EUR": 1, "BRL": 5}
            }
        }


# Translators
class ExchangeRateDataTranslator:

    def translate_raw_data(self, raw_data, date_format, max_date=None):
        """ Algorithim to perform the translation between the third party service
        and the pacs expected format.
        - raw_data: The fetched data.
        - date_format: The format in which the dates are.
        - max_date: The maximum (last) date. All dates with missing values up
            to this date will be filled with the price of the closest date."""
        rates = raw_data['rates']
        currencies = list(rates.values())[0].keys()

        # type is Dict[(str, str): float]
        # {(EUR, 2019-01-01): 9.99989182}
        data = {}
        for currency in currencies:
            for date, rate in rates.items():
                data[(currency, date)] = rate[currency]

        # Fill missing dates
        mindate = min(k[1] for k in data.keys())
        maxdate = max_date or max(k[1] for k in data.keys())
        for cur in currencies:
            i_date = mindate
            while i_date <= maxdate:
                if (cur, i_date) not in data:
                    date_before = self._date_before_str(i_date, date_format)
                    data[cur, i_date] = data[cur, date_before]
                i_date = self._date_after_str(i_date, date_format)

        dates = set(k[1] for k in data.keys())

        out = []
        for currency in currencies:
            prices = []
            for date in dates:
                # Revert price (because we use it this way)
                price = 1 / data[(currency, date)]
                prices.append({"date": date, "price": price})
            out.append({"currency": currency, "prices": prices})

        return out

    @staticmethod
    def _date_before_str(date, date_format):
        date = datetime.strptime(date, date_format)
        date_before = date - timedelta(days=1)
        return date_before.strftime(date_format)

    @staticmethod
    def _date_after_str(date, date_format):
        date = datetime.strptime(date, date_format)
        date_after = date + timedelta(days=1)
        return date_after.strftime(date_format)
