import datetime
from decimal import Decimal
from unittest.mock import Mock

from common.testutils import PacsTestCase
from currencies.currency_converter import CurrencyPricePortifolio, DateAndPrice
from currencies.money import Money
from currencies.tests.factories import CurrencyTestFactory
from reports.view_models import CurrencyOpts, BalanceEvolutionInput


class TestCurrencyOptsAsCurrencyConversionFn(PacsTestCase):

    def test_base(self):
        date = datetime.date(2019, 1, 1)
        convert_from = CurrencyTestFactory(code="BRL")
        convert_to = CurrencyTestFactory(code="USD")
        price_portifolio = [
            CurrencyPricePortifolio(
                currency=convert_from,
                prices=[DateAndPrice(date=date, price=Decimal('0.25'))],
            ),
            CurrencyPricePortifolio(
                currency=convert_to,
                prices=[DateAndPrice(date=date, price=1)],
            ),
        ]
        currency_opts = CurrencyOpts(price_portifolio, convert_to)
        conversion_fn = currency_opts.as_currency_conversion_fn()
        exp = Money(Decimal(1), convert_to)
        res = conversion_fn(Money(Decimal(4), convert_from), date)
        assert res == exp


class TestBalanceEvolutionInputAsDict:

    def test_no_currency_opts(self):
        args = {"accounts": Mock(), "dates": Mock()}
        input_ = BalanceEvolutionInput(**args)
        assert input_.as_dict() == args

    def test_with_currency_opts(self):
        args = {"accounts": Mock(), "dates": Mock(), "currency_opts": Mock()}
        input_ = BalanceEvolutionInput(**args)
        resp = input_.as_dict()
        assert resp['currency_conversion_fn'] == (
            args['currency_opts'].as_currency_conversion_fn()
        )
