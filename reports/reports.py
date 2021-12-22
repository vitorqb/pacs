from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Callable, Dict, Iterable, List, Optional, Set, Tuple

import attr
from django.db import connection
from sqlalchemy import (
    MetaData,
    and_,
    between,
    case,
    create_engine,
    func,
    literal_column,
    select,
)
from sqlalchemy.engine import Engine

import common.utils as utils
from currencies.models import Currency
from currencies.money import Balance, Money, MoneyAggregator

if TYPE_CHECKING:
    from accounts.models import Account


A_DAY = timedelta(days=1)


@attr.s()
class BalanceEvolutionQuery:
    """A query that returns a BalanceEvolutionReport"""

    _accounts: List[Account] = attr.ib()
    _dates: List[date] = attr.ib()
    _currency_dct: Dict[int, Currency] = attr.ib(init=False)
    _currency_conversion_fn: Callable[[Money, date], Money]
    _currency_conversion_fn = attr.ib(default=lambda x, _: x)

    def __attrs_post_init__(self):
        self._currency_dct = _get_currencies_in_dct()
        self._dates = sorted(self._dates)

    def _run_query(self, acc: Account) -> Iterable[Tuple[int, Decimal, int]]:
        """Given an account, returns a tuple of
        (currency_id, quantity__sum, date_group)
        for each date group in self._dates"""
        # Usefull constants
        meta, engine = SqlAlchemyLoader.get_meta_and_engine()
        t_mov, t_tra, t_acc = SqlAlchemyLoader.get_tables(meta)
        initial_date = min(self._dates)

        # The sql statement
        date_ranges = [
            (t_tra.c.date <= initial_date, 0),  # For the initial balance
            *[
                (between(t_tra.c.date, self._dates[i - 1] + A_DAY, self._dates[i]), i)
                for i in range(1, len(self._dates))
            ],
        ]
        date_group = case(date_ranges, else_=None).label("date_group")
        x = select([t_mov.c.currency_id, func.sum(t_mov.c.quantity), date_group])
        x = x.select_from(t_mov.join(t_tra).join(t_acc))
        x = x.where(
            and_(
                t_acc.c.lft >= acc.lft,
                t_acc.c.rght <= acc.rght,
                literal_column("date_group") != None,  # noqa
            )
        )
        x = x.group_by(t_mov.c.currency_id, literal_column("date_group"))
        x = x.order_by("date_group")
        x = str(x.compile(engine, compile_kwargs={"literal_binds": True}))
        return _execute_query(x)

    def _get_quantity_per_group_and_currencies(
        self,
    ) -> Tuple[Dict[Tuple[date, Account, Currency], Decimal], Set[Currency]]:
        """Runs the query for each account, and aggregates all results into
        a dictionary with the Quantity groupped by date, Account and Currency.
        Also returns a set of all used currencies."""
        currencies: Set[Currency] = set()
        data: Dict[Tuple[date, Account, Currency], Decimal] = {}
        for account in self._accounts:
            for cur_id, quantity, date_i in self._run_query(account):
                currency = self._currency_dct[cur_id]
                dt = self._dates[date_i]
                currencies.add(currency)
                data[(dt, account, currency)] = quantity
        return data, currencies

    def _aggregate_by_account_and_data(
        self,
        currencies: Iterable[Currency],
        data: Dict[Tuple[date, Account, Currency], Decimal],
    ) -> List[BalanceEvolutionReportData]:
        """Given the data quantity groupped by date, account and currency,
        and a set of all currencies, construct a list of all balance evolution
        report data.
        ASSUMES THAT data IS ORDERED BY DATE"""
        money_agg: Dict[Account, MoneyAggregator]
        money_agg = defaultdict(lambda: MoneyAggregator())

        out: List[BalanceEvolutionReportData] = []
        for account in self._accounts:
            for dt in self._dates:
                for currency in currencies:
                    q: Optional[Decimal] = data.get((dt, account, currency), None)
                    if q is not None:
                        money = Money(q, currency)
                        converted_money = self._currency_conversion_fn(money, dt)
                        money_agg[account].append_money(converted_money)
                balance: Balance = money_agg[account].as_balance()
                out.append(BalanceEvolutionReportData(dt, account, balance))
        return out

    def run(self) -> BalanceEvolutionReport:
        # Prepares a dict with Quantity for each account, currency and date
        data: Dict[Tuple[date, Account, Currency], Decimal]
        currencies: Set[Currency]
        (data, currencies) = self._get_quantity_per_group_and_currencies()

        # Sums the quantity for each account, date and currency
        out: List[BalanceEvolutionReportData]
        out = self._aggregate_by_account_and_data(currencies, data)

        return BalanceEvolutionReport(out)


@attr.s()
class BalanceEvolutionReport:
    """A report representing the balance for a set of accounts at some
    specific dates"""

    data: List[BalanceEvolutionReportData] = attr.ib()


@attr.s(frozen=True)
class BalanceEvolutionReportData:
    """A piece of data for the Balance Evolution report."""

    date: date = attr.ib()
    account: Account = attr.ib()
    balance: Balance = attr.ib()


@attr.s(frozen=True)
class Flow:
    period: Period = attr.ib()
    moneys: List[Money] = attr.ib()


@attr.s(frozen=True)
class AccountFlows:
    account: Account = attr.ib()
    flows: List[Flow] = attr.ib()


@attr.s()
class FlowEvolutionQuery:
    """Represents a query for a sequence of flow evolution."""

    # The accounts for the report
    accounts: List[Account] = attr.ib()
    # The periods for the report
    periods: List[Period] = attr.ib()
    # And optional function used to convert Money to a specific currency.
    currency_conversion_fn: Callable[[Money, date], Money]
    currency_conversion_fn = attr.ib(default=lambda x, _: x)

    def run(self) -> List[AccountFlows]:
        """Runs the query and returns a report"""
        currencies_dct = _get_currencies_in_dct()
        return [self._get_flows_for(account, currencies_dct) for account in self.accounts]

    def _get_flows_for(
        self,
        account: Account,
        currencies_dct: Dict[int, Currency],
    ) -> AccountFlows:
        meta, engine = SqlAlchemyLoader.get_meta_and_engine()
        t_mov, t_tra, t_acc = SqlAlchemyLoader.get_tables(meta)
        query = self._get_query(self.periods, account, t_mov, t_tra, t_acc)
        compiled_query = _compile_sql_alchemy_query(query, engine)
        queried_data = _execute_query(compiled_query)
        return self._query_data_to_account_flows(
            account=account,
            queried_data=queried_data,
            periods=self.periods,
            currencies_dct=currencies_dct,
            currency_conversion_fn=self.currency_conversion_fn,
        )

    @staticmethod
    def _get_query(periods: List[Period], account: Account, t_mov, t_tra, t_acc):
        """Returns an sql alchemy query that yields
        (currency_id, sum(quantity), date, period_index)
        For each period.
        """
        period_index_expr = case(
            [(between(t_tra.c.date, p.start, p.end), i) for i, p in enumerate(periods, 1)], else_=-1
        ).label("period_index")
        period_index_literal = literal_column("period_index")
        x = select(
            [
                t_mov.c.currency_id,
                func.sum(t_mov.c.quantity),
                t_tra.c.date,
                period_index_expr,
            ]
        )
        x = x.select_from(t_mov.join(t_tra).join(t_acc))
        x = x.where(
            and_(
                t_acc.c.lft >= account.lft,
                t_acc.c.rght <= account.rght,
                period_index_literal != -1,
            )
        )
        x = x.group_by(t_mov.c.currency_id, t_tra.c.date, period_index_literal)
        x = x.order_by(t_tra.c.date)
        return x

    @staticmethod
    def _query_data_to_account_flows(
        account: Account,
        queried_data: Iterable[Tuple[int, Decimal, date, int]],
        periods: List[Period],
        currencies_dct: Dict[int, Currency],
        currency_conversion_fn: Callable[[Money, date], Money],
    ) -> AccountFlows:
        period_index_money_aggregator_dct: Dict[int, MoneyAggregator]
        period_index_money_aggregator_dct = defaultdict(lambda: MoneyAggregator())

        for (cur_id, quantity, date_, period_index) in queried_data:
            currency = currencies_dct[cur_id]
            orig_currency_money = Money(currency=currency, quantity=quantity)
            final_currency_money = currency_conversion_fn(
                orig_currency_money,
                date_,
            )
            period_index_money_aggregator_dct[period_index].append_money(final_currency_money)

        account_flows: List[Flow] = []
        for i, period in enumerate(periods, 1):
            moneys = period_index_money_aggregator_dct[i].get_moneys()
            flow = Flow(period=period, moneys=moneys)
            account_flows.append(flow)

        return AccountFlows(account=account, flows=account_flows)


@attr.s()
class Period:
    """Represents a period of time, with a start and an end"""

    start: date = attr.ib()
    end: date = attr.ib()

    @classmethod
    def from_strings(cls, start_str, end_str):
        start = _str_to_date(start_str)
        end = _str_to_date(end_str)
        return Period(start, end)


class SqlAlchemyLoader:
    """Provides asqlalchemy 'engine' and a 'meta' objects, loading them
    lazy on request and caching them once loaded."""

    _cached_meta: Optional[MetaData] = None
    _cached_engine: Optional[Engine] = None

    @classmethod
    def get_meta_and_engine(cls) -> Tuple[MetaData, Engine]:
        if cls._cached_engine is None or cls._cached_engine is None:
            cls._cached_engine = create_engine(f'sqlite:///{connection.settings_dict["NAME"]}')
            cls._cached_meta = MetaData()
            cls._cached_meta.reflect(bind=cls._cached_engine)
        return cls._cached_meta, cls._cached_engine

    @staticmethod
    def get_tables(meta):
        tabs = ["movements_movement", "movements_transaction", "accounts_account"]
        return tuple(meta.tables[x] for x in tabs)

    @classmethod
    def reset_cache(cls) -> None:
        cls._cached_engine = None
        cls._cached_meta = None


def _compile_sql_alchemy_query(query, engine):
    return str(query.compile(engine, compile_kwargs={"literal_binds": True}))


def _execute_query(str_query):
    with connection.cursor() as cursor:
        yield from cursor.execute(str_query)


def _str_to_date(x):
    return datetime.strptime(x, utils.DATE_FORMAT).date()


def _get_currencies_in_dct() -> Dict[int, Currency]:
    return dict((c.pk, c) for c in Currency.objects.all())
