from unittest.mock import Mock, patch, call
from common.test import PacsTestCase
from accounting.serializers import JournalSerializer, BalanceSerializer, MoneySerializer
from accounting.balance import Journal, Balance, Money
from movements.serializers import TransactionSerializer


class TestJournalSerializer(PacsTestCase):

    def test_serializes_account_as_pk(self):
        account = Mock(pk=12)
        transaction = Mock(pk=1, get_movements_specs=[])
        transaction.get_moneys_for_account.return_value = []
        balance = Mock()
        balance.get_moneys.return_value = []
        journal = Journal(account, balance, [transaction])
        assert JournalSerializer(journal).data['account'] == 12

    @patch.object(BalanceSerializer, "to_representation")
    def test_serializes_initial_balance(self, m_to_representation):
        initial_balance = Mock()
        journal = Journal(Mock(), initial_balance, [])
        assert JournalSerializer(journal).data['initial_balance'] ==\
            m_to_representation.return_value
        assert m_to_representation.call_args == call(initial_balance)

    @patch.object(TransactionSerializer, "to_representation")
    def test_serializes_transactions(self, m_to_representation):
        transactions = [Mock(), Mock()]
        transactions[0].get_moneys_for_account.return_value = []
        transactions[1].get_moneys_for_account.return_value = []

        balance = Mock()
        balance.get_moneys.return_value = []

        journal = Journal(Mock(), balance, transactions)
        assert JournalSerializer(journal).data['transactions'] ==\
            [m_to_representation(), m_to_representation()]
        assert m_to_representation.call_args_list[0] ==\
            call(transactions[0])

    @patch.object(BalanceSerializer, "to_representation")
    def test_serializes_balances_from_get_balances(
            self,
            m_to_representation
    ):
        m_Journal = Mock()
        m_Journal().transactions = []
        m_Journal().get_balances = [Mock(), Mock()]
        serializer = JournalSerializer(m_Journal())
        assert serializer.data['balances'] == [m_to_representation.return_value] * 2
        assert m_to_representation.call_args_list[1] == \
            call(m_Journal().get_balances[0])
        assert m_to_representation.call_args_list[2] == \
            call(m_Journal().get_balances[1])


class TestBalanceSerializer(PacsTestCase):

    @patch.object(MoneySerializer, 'to_representation')
    def test_serializes_as_list_of_moneys(self, m_to_representation):
        currency_one, currency_two = Mock(), Mock()
        balance = Mock()
        balance.get_moneys.return_value = [
            Money('20', currency_one),
            Money('30', currency_two),
        ]
        serializer = BalanceSerializer(balance)

        assert serializer.data == [m_to_representation.return_value] * 2
        assert m_to_representation.call_args_list[0] ==\
            call(Money('20', currency_one))
        assert m_to_representation.call_args_list[1] ==\
            call(Money('30', currency_two))
