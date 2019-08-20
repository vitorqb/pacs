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
from reports.reports import (AccountFlows, FlowEvolutionQuery, Period, SqlAlchemyLoader, Flow, BalanceEvolutionQuery, BalanceEvolutionReport, BalanceEvolutionReportData)

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


class TestIntegrationBalanceEvolutionQuery(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.populate_accounts()
        self.populate_currencies()

    def test_integration(self):
        # An account hierarchy
        revenues_account = AccountTestFactory.create(acc_type=AccTypeEnum.BRANCH)
        assets_account = AccountTestFactory.create(acc_type=AccTypeEnum.BRANCH)
        expenses_account = AccountTestFactory.create(acc_type=AccTypeEnum.BRANCH)

        salary_account = AccountTestFactory.create(parent=revenues_account)
        cash_account = AccountTestFactory.create(parent=assets_account)
        supermarket_account = AccountTestFactory.create(parent=expenses_account)

        # The dates
        dates = [date(2019, 8, 1), date(2019, 9, 1)]

        # Give them some transactions
        salary_transaction = TransactionTestFactory.create(
            date_='2019-07-01',
            movements_specs__0__account=salary_account,
            movements_specs__1__account=cash_account,
        )
        supermarket_transaction = TransactionTestFactory.create(
            date_='2019-08-15',
            movements_specs__0__account=cash_account,
            movements_specs__1__account=supermarket_account,
        )

        # Run the query
        query = BalanceEvolutionQuery(
            accounts=[revenues_account, assets_account, expenses_account],
            dates=dates
        )
        report = query.run()
        exp = BalanceEvolutionReport(data=[
            BalanceEvolutionReportData(
                date=dates[0],
                account=revenues_account,
                balance=salary_transaction.get_balance_for_account(revenues_account),
            ),
            BalanceEvolutionReportData(
                date=dates[1],
                account=revenues_account,
                balance=salary_transaction.get_balance_for_account(revenues_account),
            ),
            BalanceEvolutionReportData(
                date=dates[0],
                account=assets_account,
                balance=salary_transaction.get_balance_for_account(assets_account),
            ),
            BalanceEvolutionReportData(
                date=dates[1],
                account=assets_account,
                balance=(
                    salary_transaction.get_balance_for_account(assets_account)
                    +
                    supermarket_transaction.get_balance_for_account(assets_account)
                )
            ),
            BalanceEvolutionReportData(
                date=dates[0],
                account=expenses_account,
                balance=Balance([]),
            ),
            BalanceEvolutionReportData(
                date=dates[1],
                account=expenses_account,
                balance=supermarket_transaction.get_balance_for_account(
                    expenses_account
                ))
        ])
        assert exp == report


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
