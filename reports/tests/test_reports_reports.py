from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, call, patch, sentinel

from django.conf import settings

from accounts.models import AccTypeEnum
from accounts.tests.factories import AccountTestFactory
from common.models import list_to_queryset
from common.test import PacsTestCase
from currencies.money import Balance, Money
from currencies.tests.factories import CurrencyTestFactory
from movements.tests.factories import TransactionTestFactory
from reports.reports import (AccountFlows, BalanceEvolution,
                             BalanceEvolutionData, BalanceEvolutionQuery,
                             FlowEvolutionQuery, Period, SqlAlchemyLoader,
                             Flow)

from .factories import PeriodTestFactory

A_DAY = timedelta(days=1)


@patch('reports.reports.create_engine')
@patch('reports.reports.MetaData')
class TestSqlAlchemyLoader(PacsTestCase):

    def tearDown(self):
        super().tearDown()
        SqlAlchemyLoader.reset_cache()

    def test_returns_meta(self, m_MetaData, m_create_engine):
        meta, engine = SqlAlchemyLoader.get_meta_and_engine()
        # MetaData was called to generate meta
        assert m_MetaData.call_args_list == [call()]
        assert meta is m_MetaData.return_value
        # MetaData.bind was called with this engine
        assert meta.reflect.call_args_list == [call(bind=engine)]

    def test_returns_engine(self, m_MetaData, m_create_engine):
        meta, engine = SqlAlchemyLoader.get_meta_and_engine()
        assert m_create_engine.call_args_list == [call(
            f'sqlite:///{settings.DATABASES["default"]["TEST"]["NAME"]}'
        )]
        assert engine is m_create_engine.return_value

    def test_caches_result(self, m_MetaData, m_create_engine):
        m_MetaData.side_effect = [Mock(), Mock()]
        m_create_engine.side_effect = [Mock(), Mock()]
        one = SqlAlchemyLoader.get_meta_and_engine()
        two = SqlAlchemyLoader.get_meta_and_engine()
        for i in range(2):
            assert one[i] is two[i]


class TestBalanceEvolutionQuery(PacsTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.populate_accounts()
        # Set up some unrelated transactions that should not affect the results
        TransactionTestFactory.create_batch(3)
        # An account to be used always
        cls.account = AccountTestFactory.create()

    def test__get_evolution_data_empty_accounts(self):
        query = BalanceEvolutionQuery(accounts=[], periods=[PeriodTestFactory()])
        assert query._get_evolution_data() == []

    def test_empty_periods_raises_error(self):
        with self.assertRaises(ValueError):
            BalanceEvolutionQuery(accounts=[], periods=[])

    def test__get_evolution_data_single_accounts_multiple_periods(self):
        # 3 transactions for the account
        transactions = TransactionTestFactory.create_batch(
            3,
            movements_specs__0__account=self.account
        )
        transactions_qset = list_to_queryset(transactions)

        # Construct periods
        first_date = min(x.get_date() for x in transactions)
        last_date = max(x.get_date() for x in transactions)
        period_before = Period(first_date - (2*A_DAY), first_date - A_DAY)
        period_during = Period(first_date, last_date)

        # Now put an extra transaction after the last_date
        TransactionTestFactory.create(date_=last_date + A_DAY)

        # Runs the query
        query = BalanceEvolutionQuery(
            accounts=[self.account],
            periods=[period_before, period_during]
        )
        resp = query._get_evolution_data()
        assert len(resp) == 1

        # Initial balance should be zero
        assert resp[0].initial_balance == Balance([])
        # The first period should be zero, the second should contain the balance
        # for the transactions in the period
        assert resp[0].balance_evolution == [
            Balance([]),
            transactions_qset.get_balance_for_account(self.account),
        ]

    def test__get_evolution_data_get_initial_value_right(self):
        transaction = TransactionTestFactory.create(
            movements_specs__0__account=self.account
        )
        date_ = transaction.get_date()
        periods = [Period(date_ + A_DAY, date_ + (2*A_DAY))]
        query = BalanceEvolutionQuery([self.account], periods)
        resp = query._get_evolution_data()
        assert len(resp) == 1
        assert resp[0].initial_balance == (
            transaction.get_balance_for_account(self.account)
        )

    def test__get_evolution_data_get_for_parent_account(self):
        parent = AccountTestFactory.create(acc_type=AccTypeEnum.BRANCH)
        child = AccountTestFactory.create(parent=parent)
        date_ = date(2018, 12, 22)
        cur = CurrencyTestFactory.create()
        TransactionTestFactory.create(
            date_=date_,
            movements_specs__0__account=child,
            movements_specs__0__money__quantity=Decimal('25'),
            movements_specs__0__money__currency=cur,
            movements_specs__1__money__currency=cur,
            movements_specs__1__money__quantity=Decimal('-25'),
        )
        query = BalanceEvolutionQuery(
            [parent],
            [Period(date_ + A_DAY, date_ + (2*A_DAY))]
        )
        resp = query._get_evolution_data()
        assert len(resp) == 1
        assert resp[0].initial_balance == Balance([Money('25', cur)])
        assert resp[0].balance_evolution == [Balance([])]

    def test_get_evolution_data_many_two_periods(self):
        tra = TransactionTestFactory.create(
            movements_specs__0__account=self.account
        )
        bal = tra.get_balance_for_account(self.account)
        date_ = tra.get_date()
        date_before = date_ - A_DAY
        periods = [
            Period(date_ - (2*A_DAY), date_ - A_DAY),
            Period(date_, date_ + A_DAY)
        ]

        other_acc = AccountTestFactory.create()
        other_tra = TransactionTestFactory.create(
            date_=date_before,
            movements_specs__0__account=other_acc
        )
        other_bal = other_tra.get_balance_for_account(other_acc)

        query = BalanceEvolutionQuery([self.account, other_acc], periods)
        resp = query._get_evolution_data()
        assert resp == [
            BalanceEvolutionData(
                account=self.account,
                initial_balance=Balance([]),
                balance_evolution=[Balance([]), bal]
            ),
            BalanceEvolutionData(
                account=other_acc,
                initial_balance=Balance([]),
                balance_evolution=[other_bal, Balance([])]
            )
        ]

    def test_run(self):
        query = BalanceEvolutionQuery([Mock()], [Mock()])
        with patch.object(query, '_get_evolution_data') as m_get_evolution_data:
            resp = query.run()
        assert resp == BalanceEvolution(
            periods=query.periods,
            data=m_get_evolution_data.return_value
        )


class TestFlowEvolutionQuery:

    @staticmethod
    def patch_get_flows_for(return_value):
        return patch.object(
            FlowEvolutionQuery,
            '_get_flows_for',
            return_value=return_value
        )

    @staticmethod
    def patch_get_currencies_in_dct():
        return patch('reports.reports._get_currencies_in_dct', autospec=True)

    def test_run(self):
        accounts = [Mock(), Mock()]
        periods = [Mock(), Mock()]
        with self.patch_get_flows_for(return_value=sentinel.acc_flows) as get_flows_for:
            with self.patch_get_currencies_in_dct() as get_currencies_in_dct:
                res = FlowEvolutionQuery(accounts, periods).run()
        assert res == [sentinel.acc_flows for acc in accounts]
        assert get_flows_for.call_args_list == [
            call(acc, get_currencies_in_dct()) for acc in accounts
        ]


class TestIntegrationFlowEvolutionQuery(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.populate_accounts()
        self.populate_currencies()

    def test_integration(self):
        # An account hierarchy
        current_account_acc = AccountTestFactory()
        expenses_acc = AccountTestFactory(acc_type=AccTypeEnum.BRANCH)
        house_expenses_acc = AccountTestFactory(parent=expenses_acc)
        car_expenses_acc = AccountTestFactory(parent=expenses_acc)
        # The periods
        periods = [
            Period.from_strings('2017-01-01', '2017-12-31'),
            Period.from_strings('2018-01-01', '2018-12-31'),
        ]
        # Two transactions for the first period
        house_expense_tra = TransactionTestFactory(
            date_='2017-01-01',
            movements_specs__0__account=current_account_acc,
            movements_specs__1__account=house_expenses_acc,
        )
        car_expense_tra = TransactionTestFactory(
            date_='2017-12-31',
            movements_specs__0__account=current_account_acc,
            movements_specs__1__account=car_expenses_acc,
        )
        # One outside the periods
        outside_house_expense_tra = TransactionTestFactory(
            date_='2016-12-31',
            movements_specs__0__account=current_account_acc,
            movements_specs__1__account=house_expenses_acc,
        )
        # Makes the report
        query_accounts = [current_account_acc, expenses_acc]
        query = FlowEvolutionQuery(accounts=query_accounts, periods=periods)
        account_flows = query.run()
        # We should have two flows, one for each account
        assert [x.account for x in account_flows] == query_accounts
        # And now let's test the flow for the first account
        current_account_flows = account_flows[0].flows
        assert current_account_flows == [
            Flow(
                period=periods[0],
                moneys=(
                    car_expense_tra.get_balance_for_account(current_account_acc)
                    +
                    house_expense_tra.get_balance_for_account(current_account_acc)
                ).get_moneys()
            ),
            Flow(period=periods[1], moneys=[]),
        ]
        # And for the second
        expenses_account_flows = account_flows[1].flows
        assert expenses_account_flows == [
            Flow(
                period=periods[0],
                moneys=(
                    car_expense_tra.get_balance_for_account(expenses_acc)
                    +
                    house_expense_tra.get_balance_for_account(expenses_acc)
                ).get_moneys()
            ),
            Flow(period=periods[1], moneys=[]),
        ]


class TestPeriod:

    def test_from_strings(self):
        date_str_one = '2019-01-01'
        date_one = date(2019, 1, 1)
        date_str_two = '2019-12-31'
        date_two = date(2019, 12, 31)
        period = Period.from_strings(date_str_one, date_str_two)
        assert period == Period(date_one, date_two)
