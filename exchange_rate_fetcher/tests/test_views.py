from unittest import TestCase
from unittest.mock import Mock

import exchange_rate_fetcher.views as sut
from exchange_rate_fetcher.view_models import ExchangeRateDataInputs


class ExchangeRateDataViewSpecTest(TestCase):

    def test_serialize_inputs(self):
        start_at = "2020-02-04"
        end_at = "2020-02-05"
        currency_codes = "EUR,BRL"
        query_params = {"start_at": start_at,
                        "end_at": end_at,
                        "currency_codes": currency_codes}
        request = Mock(query_params=query_params)
        result = sut.ExchangeRateDataViewSpec._serialize_inputs(request)
        assert result\
            == ExchangeRateDataInputs(start_at, end_at, ["EUR", "BRL"])
