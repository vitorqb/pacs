from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple

import attr
from django.db import connection
from sqlalchemy import (MetaData, and_, between, case, create_engine, func,
                        literal_column, select)
from sqlalchemy.engine import Engine

from currencies.models import Currency
from currencies.money import Balance, Money

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
        t_mov = meta.tables['movements_movement']
        t_tra = meta.tables['movements_transaction']
        t_acc = meta.tables['accounts_account']
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


@attr.s()
class Period:
    """ Represents a period of time, with a start and an end """
    start: date = attr.ib()
    end: date = attr.ib()


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

    @classmethod
    def reset_cache(cls) -> None:
        cls._cached_engine = None
        cls._cached_meta = None
