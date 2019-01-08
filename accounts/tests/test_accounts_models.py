from rest_framework.exceptions import ValidationError

from accounts.management.commands.populate_accounts import (account_populator,
                                                            account_type_populator)
from accounts.models import (Account, AccountFactory, AccountType, AccTypeEnum,
                             get_root_acc)
from common.test import PacsTestCase

from .factories import AccountTestFactory


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


class TestAccount(AccountsModelTestCase):

    def test_get_acc_type(self):
        acc = AccountTestFactory()
        exp_acc_type = next(
            x
            for x in AccTypeEnum
            if x.value == acc.acc_type.name
        )
        assert acc.get_acc_type() == exp_acc_type
