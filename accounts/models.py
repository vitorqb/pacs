from enum import Enum
from pyrsistent import freeze
import attr

import django.db.models as m

from rest_framework.exceptions import ValidationError

from mptt.models import MPTTModel, TreeForeignKey
from common.models import NameField, full_clean_and_save


@attr.s()
class AccountFactory():
    """ Encapsulates the creation of Account """

    ERR_MSGS = freeze({
        'ACC_TYPE_NEW_ACCOUNTS_NOT_ALLOWED': (
            'Account type "{}" does not allow new accounts'
        ),
    })

    def __call__(self, name, acc_type, parent):
        """ Creates a new account. `acc_type` must be one of AccTypeEnum,
        and `parent` must be an Account """
        assert acc_type in AccTypeEnum
        acc_type_obj = AccountType.objects.get(name=acc_type.value)
        self._validate_acc_type_obj(acc_type_obj)
        acc = Account(
            name=name,
            acc_type=acc_type_obj,
        )
        acc.full_clean()
        acc.set_parent(parent)
        return full_clean_and_save(acc)

    def _validate_acc_type_obj(self, acc_type_obj):
        if acc_type_obj.new_accounts_allowed is False:
            m = self.ERR_MSGS['ACC_TYPE_NEW_ACCOUNTS_NOT_ALLOWED']
            raise ValidationError(m.format(acc_type_obj.name))


class Account(MPTTModel):
    """ An Account, a tree structure to host movements. """
    #
    # Fields
    #
    name = NameField()
    acc_type = m.ForeignKey('AccountType', on_delete=m.CASCADE)
    parent = TreeForeignKey(
        'self',
        on_delete=m.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )

    #
    # Constants
    #
    ERR_MSGS = freeze({
        'NULL_PARENT': '`parent` can not be None.',
        'PARENT_CHILD_NOT_ALLOWED': 'Parent account {} does not allows children.'
    })

    #
    # Methods
    #
    def get_name(self):
        return self.name

    def set_name(self, x):
        self.name = x
        full_clean_and_save(self)

    def get_parent(self):
        """ Returns the parent. Can be None for the Root Account. """
        return self.parent

    def set_parent(self, parent):
        if parent is None:
            msg = {'parent': self.ERR_MSGS['NULL_PARENT']}
            raise ValidationError(msg)
        if not parent.allows_children():
            msg = self.ERR_MSGS['PARENT_CHILD_NOT_ALLOWED']
            raise ValidationError({'parent': msg.format(parent)})
        self.parent = parent
        full_clean_and_save(self)

    def get_acc_type(self):
        """ Getter for acc_type. Notice that instead of returning an
        AccountType objects, we return AccTypeEnum. This is because
        AccountType should only be known by this module. """
        for acc_type in AccTypeEnum:
            if acc_type.value == self.acc_type.name:
                return acc_type

    def allows_children(self):
        """ Returns True if this account can be the parent of other accounts,
        else False"""
        return self.acc_type.children_allowed

    def allows_movements(self):
        """ Returns True if this account can have movements, else False """
        return self.acc_type.movements_allowed


class AccTypeEnum(Enum):
    ROOT = 'Root'
    BRANCH = 'Branch'
    LEAF = 'Leaf'


class AccountType(m.Model):
    """ A possible account type """
    name = NameField()
    children_allowed = m.BooleanField()
    movements_allowed = m.BooleanField()
    new_accounts_allowed = m.BooleanField()


# ------------------------------------------------------------------------------
# Services
def get_root_acc():
    """ Returns the root account """
    return Account.objects.get(name="Root Account")


def get_currency_price_change_rebalance_acc():
    """ Returns the account used to rebalance transactions on currency price
    changes """
    return Account.objects.get(name="Currency Price Change Compensation")
