from unittest import TestCase
import exchange_rate_fetcher.view_models as sut


class ExchangeRateDataInputsTest(TestCase):

    def test_base(self):
        start_at = "1993-11-23"
        end_at = "2020-02-04"
        currency_codes = ["BRL", "EUR"]
        inputs = sut.ExchangeRateDataInputs(start_at, end_at, currency_codes)
        assert inputs.start_at == start_at
        assert inputs.end_at == end_at
        assert inputs.currency_codes == currency_codes
