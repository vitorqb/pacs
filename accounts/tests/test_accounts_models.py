import pytest
from django.db.models import ProtectedError

from rest_framework.exceptions import ValidationError

from accounts.management.commands.populate_accounts import (account_populator,
                                                            account_type_populator)
from accounts.models import (Account, AccountFactory, AccountType, AccTypeEnum,
                             get_root_acc, AccountDestroyer)
from common.testutils import PacsTestCase

from .factories import AccountTestFactory
from movements.tests.factories import MovementTestFactory


class AccountsModelTestCase(PacsTestCase):
    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()


class TestAccountFactory(AccountsModelTestCase):

    def setUp(self):
        super().setUp()
        self.data = {
            'name': 'My Account',
            'acc_type': AccTypeEnum.BRANCH,
            'parent': get_root_acc()
        }

    def update_data(self, **kwargs):
        self.data = {**self.data, **kwargs}

    def call(self):
        return AccountFactory()(**self.data)

    def test_base_creation(self):
        acc = self.call()
        assert acc.name == self.data['name']
        assert acc.acc_type == AccountType.objects.get(name='Branch')
        assert acc.parent == get_root_acc()

    def test_invalid_account_type_raises_err(self):
        AccountType\
            .objects\
            .filter(name=self.data['acc_type'].value)\
            .update(new_accounts_allowed=False)
        errmsg = AccountFactory.ERR_MSGS['ACC_TYPE_NEW_ACCOUNTS_NOT_ALLOWED']
        errmsg = errmsg.format(self.data['acc_type'].value)
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()

    def test_invalid_parent_raises_err(self):
        self.data['parent'].acc_type.children_allowed = False
        errmsg = Account.ERR_MSGS['PARENT_CHILD_NOT_ALLOWED']
        errmsg = errmsg.format(self.data['parent'])
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()

    def test_parent_cant_be_null(self):
        self.update_data(parent=None)
        errmsg = Account.ERR_MSGS['NULL_PARENT']
        with self.assertRaisesMessage(ValidationError, errmsg):
            self.call()


class TestAccountDestroyer(AccountsModelTestCase):

    def test_base(self):
        acc = AccountTestFactory()
        acc_pk = acc.pk
        AccountDestroyer()(acc)
        assert acc_pk not in Account.objects.values_list("pk", flat=True)

    def test_validation_error_if_child(self):
        parent = AccountTestFactory(acc_type=AccTypeEnum.BRANCH)
        child = AccountTestFactory(parent=parent)
        with pytest.raises(ValidationError) as e:
            AccountDestroyer()(parent)
        assert e.value.get_codes() == ["ACCOUNT_HAS_CHILD"]

    def test_validation_error_if_movements(self):
        account = AccountTestFactory()
        movement = MovementTestFactory(account=account)
        with pytest.raises(ValidationError) as e:
            AccountDestroyer()(account)
        assert e.value.get_codes() == ["ACCOUNT_HAS_MOVEMENTS"]


class TestAccount(AccountsModelTestCase):

    def test_get_acc_type(self):
        acc = AccountTestFactory()
        exp_acc_type = next(
            x
            for x in AccTypeEnum
            if x.value == acc.acc_type.name
        )
        assert acc.get_acc_type() == exp_acc_type

    def test_get_descendants_ids(self):
        self.populate_accounts()
        root = get_root_acc()
        assert root.get_descendants_ids(True) == [
            x.id for x in Account.objects.all()
        ]

    def test_get_descendants_ids_with_cache(self):
        self.populate_accounts()
        acc = Account.objects.first()

        acc = Account.objects.filter(pk=acc.pk).first()
        with self.assertNumQueries(1):
            acc.get_descendants_ids(True)

        acc = Account.objects.filter(pk=acc.pk).first()
        with self.assertNumQueries(0):
            acc.get_descendants_ids(True, use_cache=True)

    def test_get_descendants_ids_force_no_cache(self):
        self.populate_accounts()
        acc = Account.objects.first()

        acc = Account.objects.filter(pk=acc.pk).first()
        with self.assertNumQueries(1):
            acc.get_descendants_ids(True)

        acc = Account.objects.filter(pk=acc.pk).first()
        with self.assertNumQueries(1):
            acc.get_descendants_ids(True, use_cache=False)

    def test_cant_delete_if_has_movement(self):
        mov = MovementTestFactory()
        acc = mov.account
        with pytest.raises(ProtectedError):
            acc.delete()

    def test_cant_delete_if_has_children(self):
        parent = AccountTestFactory(acc_type=AccTypeEnum.BRANCH)
        child = AccountTestFactory(parent=parent)
        with pytest.raises(ProtectedError):
            parent.delete()

    def test_can_delete_if_no_movement(self):
        acc = AccountTestFactory()
        acc_pk = acc.pk
        acc.delete()
        assert acc_pk not in Account.objects.values_list('pk', flat=True)
