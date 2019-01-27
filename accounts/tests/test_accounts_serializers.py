from unittest.mock import Mock, call, patch, MagicMock

from rest_framework.exceptions import ValidationError

from accounts.journal import Journal
from accounts.management.commands.populate_accounts import (account_populator,
                                                            account_type_populator)
from accounts.models import Account, AccTypeEnum, get_root_acc
from accounts.serializers import (AccountSerializer, AccTypeField,
                                  JournalSerializer)
from common.test import PacsTestCase
from currencies.serializers import BalanceSerializer
from movements.serializers import TransactionSerializer

from .factories import AccountTestFactory


class TestAccTypeField(PacsTestCase):

    def setUp(self):
        super().setUp()
        self.field = AccTypeField()

    def test_to_internal_value(self):
        for acc_type in AccTypeEnum:
            with self.subTest(acc_type):
                value = acc_type.value.lower()
                parsed = self.field.to_internal_value(value)
                assert parsed == acc_type

    def test_to_internal_value_wrong_raises_validation_error(self):
        unkown_type = "alo213h21"
        assert unkown_type not in set(x.value for x in AccTypeEnum)
        with self.assertRaises(ValidationError):
            self.field.to_internal_value(unkown_type)

    def test_to_representation(self):
        for acc_type in AccTypeEnum:
            with self.subTest(acc_type=acc_type):
                assert self.field.to_representation(acc_type) == acc_type.value


class TestAccountSerializer_creation(PacsTestCase):

    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()
        self.data = {
            "name": "Acc",
            "acc_type": AccTypeEnum.LEAF.value,
            "parent": get_root_acc().pk
        }

    def create(self):
        """ Creates using the serializer and self.data """
        ser = AccountSerializer(data=self.data)
        ser.is_valid(True)
        return ser.save()

    def test_create_account(self):
        acc = self.create()
        assert acc.get_name() == self.data['name']
        assert acc in Account.objects.all()

    def test_create_acc_repeated_name_raises_validation_error(self):
        acc = AccountTestFactory()
        self.data['name'] = acc.get_name()
        with self.assertRaises(ValidationError) as e:
            self.create()
        assert 'name' in e.exception.detail

    def test_create_acc_pk_is_ignored_if_parsed(self):
        self.data['pk'] = 123
        acc = self.create()
        assert acc.pk != self.data['pk']


class TestAccountSerializer_update(PacsTestCase):
    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()
        self.acc = AccountTestFactory()
        self.data = {}

    def update(self):
        """ Updates using serializer and self.data """
        ser = AccountSerializer(self.acc, data=self.data, partial=True)
        ser.is_valid(True)
        return ser.save()

    def test_acc_type_is_imutable(self):
        self.acc = AccountTestFactory(acc_type=AccTypeEnum.LEAF)
        self.data['acc_type'] = AccTypeEnum.BRANCH.value
        with self.assertRaises(ValidationError) as e:
            self.update()
        assert 'acc_type' in e.exception.detail

    def test_acc_type_does_not_raises_if_equal_to_current(self):
        self.data['acc_type'] = self.acc.get_acc_type().value
        try:
            self.update()
        except ValidationError as e:
            self.fail(f"Should not have raised ValidationError: {str(e)}")

    def test_update_name_and_parent(self):
        other_acc = AccountTestFactory(acc_type=AccTypeEnum.BRANCH)
        new_name = "New name"
        assert self.acc.get_name != new_name

        self.data['parent'] = other_acc.pk
        self.data['name'] = "New name"
        self.update()

        self.acc.refresh_from_db()
        assert self.acc.get_name() == new_name
        assert self.acc.get_parent() == other_acc

    def test_update_parent_that_cant_have_child_raises_err(self):
        new_parent = AccountTestFactory(acc_type=AccTypeEnum.LEAF)
        assert new_parent.allows_children() is False

        self.data['parent'] = new_parent.pk
        with self.assertRaises(ValidationError) as e:
            self.update()
        assert 'parent' in e.exception.detail


class TestJournalSerializer(PacsTestCase):

    def test_serializes_account_as_pk(self):
        account = Mock(pk=12)
        transaction = Mock(
            pk=1,
            get_movements_specs=[],
            get_moneys_for_account=Mock(return_value=[])
        )
        m_transactions_qset = MagicMock(iterator=Mock(return_value=[transaction]))
        m_transactions_qset.__iter__.return_value = [transaction]
        balance = Mock(get_moneys=Mock(return_value=[]))
        journal = Journal(account, balance, m_transactions_qset)
        assert JournalSerializer(journal).data['account'] == 12

    @patch.object(BalanceSerializer, "to_representation")
    def test_serializes_initial_balance(self, m_to_representation):
        initial_balance = Mock()
        m_transactions_qset = MagicMock()
        m_transactions_qset.iterator.return_value = []
        m_transactions_qset.__iter__.return_value = []
        journal = Journal(Mock(), initial_balance, m_transactions_qset)
        assert JournalSerializer(journal).data['initial_balance'] ==\
            m_to_representation.return_value
        assert m_to_representation.call_args == call(initial_balance)

    @patch.object(TransactionSerializer, "to_representation")
    def test_serializes_transactions(self, m_to_representation):
        transactions = [Mock(), Mock()]
        transactions[0].get_moneys_for_account.return_value = []
        transactions[1].get_moneys_for_account.return_value = []
        m_transactions_qset = MagicMock()
        m_transactions_qset.iterator.return_value = transactions
        m_transactions_qset.__iter__.return_value = transactions

        balance = Mock()
        balance.get_moneys.return_value = []

        journal = Journal(Mock(), balance, m_transactions_qset)
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
