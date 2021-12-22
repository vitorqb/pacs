from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List, Union

import attr

from currencies.currency_converter import CurrencyPricePortifolioConverter

if TYPE_CHECKING:
    from accounts.models import Account
    from currencies.currency_converter import CurrencyPricePortifolio
    from currencies.models import Currency
    from reports.reports import Period


NOINPUT = object()


@attr.s(frozen=True)
class CurrencyOpts:
    price_portifolio: List[CurrencyPricePortifolio] = attr.ib()
    convert_to: Currency = attr.ib()

    def as_currency_conversion_fn(self):
        converter = CurrencyPricePortifolioConverter(price_portifolio_list=self.price_portifolio)
        return lambda m, d: converter.convert(m, self.convert_to, d)


@attr.s(frozen=True)
class FlowEvolutionInput:
    periods: List[Period] = attr.ib()
    accounts: List[Account] = attr.ib()
    currency_opts: CurrencyOpts = attr.ib()


@attr.s(frozen=True)
class BalanceEvolutionInput:
    accounts: List[Account] = attr.ib()
    dates: List[date] = attr.ib()
    currency_opts: Union[CurrencyOpts, NOINPUT] = attr.ib(default=NOINPUT)

    def as_dict(self):
        out = {"accounts": self.accounts, "dates": self.dates}
        if self.currency_opts is not NOINPUT:
            out["currency_conversion_fn"] = self.currency_opts.as_currency_conversion_fn()
        return out
