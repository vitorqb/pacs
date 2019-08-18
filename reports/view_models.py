from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List

import attr

if TYPE_CHECKING:
    from reports.reports import Period
    from accounts.models import Account
    from currencies.models import Currency
    from currencies.currency_converter import CurrencyPricePortifolio


@attr.s(frozen=True)
class CurrencyOpts:
    price_portifolio: List[CurrencyPricePortifolio] = attr.ib()
    convert_to: Currency = attr.ib()


@attr.s(frozen=True)
class FlowEvolutionInput:
    periods: List[Period] = attr.ib()
    accounts: List[Account] = attr.ib()
    currency_opts: CurrencyOpts = attr.ib()


@attr.s(frozen=True)
class BalanceEvolutionInput:
    accounts: List[Account] = attr.ib()
    dates: List[date] = attr.ib()
