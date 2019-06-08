from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple, Set, Callable

import attr
from django.db import connection
from sqlalchemy import (MetaData, and_, between, case, create_engine, func,
                        literal_column, select)
from sqlalchemy.engine import Engine

from currencies.models import Currency
from currencies.money import Balance, Money, MoneyAggregator

if TYPE_CHECKING:
    from accounts.models import Account


@attr.s()
class BalanceEvolution:
    """ The BalanceEvolution report. It reports the evolution of the
    balances of a set of accounts over some periods. """
    periods: List[Period] = attr.ib()
    data: List[BalanceEvolutionData] = attr.ib()


@attr.s()
class BalanceEvolutionData:
    """ Represents the balance evolution data for a single account """
    account: Account = attr.ib()
    initial_balance: Balance = attr.ib()
    balance_evolution: List[Balance] = attr.ib()


@attr.s()
class BalanceEvolutionQuery:
    """ Represents a query that returns the BalanceEvolution for a
    list of accounts over some periods """
    accounts: List[Account] = attr.ib()
    periods: List[Period] = attr.ib()

    @periods.validator
    def period_validator(self, attribute, periods):
        if len(periods) == 0:
            raise ValueError("At least one period is needed")

    def run(self) -> BalanceEvolution:
        """ Runs the query and returns a BalanceEvolution """
        data = self._get_evolution_data()
        return BalanceEvolution(periods=self.periods, data=data)

    def _get_evolution_data(self) -> List[BalanceEvolutionData]:
        # Caches currencies for efficiency
        currencies = dict((c.pk, c) for c in Currency.objects.all())
        # Number of results = initial_period + periods
        result_len = 1 + len(self.periods)

        with connection.cursor() as cursor:
            out: List[BalanceEvolutionData] = []
            for acc in self.accounts:
                balances_dct: Dict[int, Balance] = defaultdict(lambda: Balance([]))
                for (cur_id, quantity, date_group) in self._run_query(acc, cursor):
                    current_balance = balances_dct[date_group]
                    money_to_add = Money(quantity, currencies[cur_id])
                    balances_dct[date_group] = (
                        current_balance.add_money(money_to_add)
                    )

                # Transforms the dict for balances into a list (date_group is the
                # index)
                balances_lst = [balances_dct[i] for i in range(result_len)]
                balance_evol_data = BalanceEvolutionData(
                    account=acc,
                    initial_balance=balances_lst[0],
                    balance_evolution=balances_lst[1:]
                )
                out.append(balance_evol_data)

        return out

    def _run_query(
            self,
            acc: Account,
            cursor
    ) -> Iterable[Tuple[int, Decimal, int]]:
        # Usefull constants
        meta, engine = SqlAlchemyLoader.get_meta_and_engine()
        t_mov, t_tra, t_acc = SqlAlchemyLoader.get_tables(meta)
        initial_date = min(p.start for p in self.periods)

        # The sql statement
        date_group = case(
            [
                (t_tra.c.date < initial_date, 0),  # For the initial balance
                *[
                    (between(t_tra.c.date, p.start, p.end), i)
                    for i, p in enumerate(self.periods, 1)
                ]
            ],
            else_=None
        ).label('date_group')
        x = select([t_mov.c.currency_id, func.sum(t_mov.c.quantity), date_group])
        x = x.select_from(t_mov.join(t_tra).join(t_acc))
        x = x.where(and_(
            t_acc.c.lft >= acc.lft,
            t_acc.c.rght <= acc.rght,
            literal_column('date_group') != None  # noqa
        ))
        x = x.group_by(t_mov.c.currency_id, literal_column('date_group'))
        x = x.order_by('date_group')
        x = str(x.compile(engine, compile_kwargs={"literal_binds": True}))
        return cursor.execute(x)


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
    """ Represents a query for a sequence of flow evolution. """

    # The accounts for the report
    accounts: List[Account] = attr.ib()
    # The periods for the report
    periods: List[Period] = attr.ib()
    # And optional function used to convert Money to a specific currency.
    currency_conversion_fn: Callable[[Money, date], Money]
    currency_conversion_fn = attr.ib(default=lambda x, _: x)

    def run(self) -> List[AccountFlows]:
        """ Runs the query and returns a report """
        currencies_dct = _get_currencies_in_dct()
        return [
            self._get_flows_for(account, currencies_dct)
            for account in self.accounts
        ]

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
    def _get_query(
            periods: List[Period],
            account: Account,
            t_mov,
            t_tra,
            t_acc
    ):
        """ Returns an sql alchemy query that yields
        (currency_id, sum(quantity), date, period_index)
        For each period.
        """
        period_index_expr = case(
            [(between(t_tra.c.date, p.start, p.end), i)
             for i, p in enumerate(periods, 1)],
            else_=-1
        ).label('period_index')
        period_index_literal = literal_column('period_index')
        x = select([
            t_mov.c.currency_id,
            func.sum(t_mov.c.quantity),
            t_tra.c.date,
            period_index_expr,
        ])
        x = x.select_from(t_mov.join(t_tra).join(t_acc))
        x = x.where(and_(
            t_acc.c.lft >= account.lft,
            t_acc.c.rght <= account.rght,
            period_index_literal != -1,
        ))
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
            period_index_money_aggregator_dct[period_index].append_money(
                final_currency_money
            )

        account_flows: List[Flow] = []
        for i, period in enumerate(periods, 1):
            moneys = period_index_money_aggregator_dct[i].get_moneys()
            flow = Flow(period=period, moneys=moneys)
            account_flows.append(flow)

        return AccountFlows(account=account, flows=account_flows)


@attr.s()
class Period:
    """ Represents a period of time, with a start and an end """
    start: date = attr.ib()
    end: date = attr.ib()

    @classmethod
    def from_strings(cls, start_str, end_str):
        start = _str_to_date(start_str)
        end = _str_to_date(end_str)
        return Period(start, end)


class SqlAlchemyLoader:
    """ Provides asqlalchemy 'engine' and a 'meta' objects, loading them
    lazy on request and caching them once loaded. """
    _cached_meta: Optional[MetaData] = None
    _cached_engine: Optional[Engine] = None

    @classmethod
    def get_meta_and_engine(cls) -> Tuple[MetaData, Engine]:
        if cls._cached_engine is None or cls._cached_engine is None:
            cls._cached_engine = create_engine(
                f'sqlite:///{connection.settings_dict["NAME"]}'
            )
            cls._cached_meta = MetaData()
            cls._cached_meta.reflect(bind=cls._cached_engine)
        return cls._cached_meta, cls._cached_engine

    @staticmethod
    def get_tables(meta):
        tabs = ['movements_movement', 'movements_transaction', 'accounts_account']
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
    return datetime.strptime(x, '%Y-%m-%d').date()


def _get_currencies_in_dct() -> Dict[int, Currency]:
    return dict((c.pk, c) for c in Currency.objects.all())
