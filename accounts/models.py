from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Dict, List, NoReturn

import attr
import django.db.models as m
from django.core.cache import cache
from mptt.models import MPTTModel, TreeForeignKey
from rest_framework.exceptions import ValidationError

from common.models import NameField, full_clean_and_save


@attr.s()
class AccountFactory():
    """ Encapsulates the creation of Account """

    ERR_MSGS = {
        'ACC_TYPE_NEW_ACCOUNTS_NOT_ALLOWED': (
            'Account type "{}" does not allow new accounts'
        ),
    }

    def __call__(
            self,
            name: str,
            acc_type: AccTypeEnum,
            parent: Account
    ) -> Account:
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


@attr.s()
class AccountDestroyer():
    """ Encapsulates the destruction of an Account """

    ERR_MSGS: Dict[str, str] = {
        'ACCOUNT_HAS_CHILD': "Can not delete an account that has children.",
        'ACCOUNT_HAS_MOVEMENTS': "Can not delete an account that has movements.",
    }

    @classmethod
    def fail(cls, err_code: str) -> NoReturn:
        err_msg = cls.ERR_MSGS[err_code]
        raise ValidationError(err_msg, err_code)

    @classmethod
    def validate_no_child(cls, account: Account):
        if account.count_children() != 0:
            cls.fail('ACCOUNT_HAS_CHILD')

    @classmethod
    def validate_no_movements(cls, account: Account):
        if account.count_movements() != 0:
            cls.fail('ACCOUNT_HAS_MOVEMENTS')

    def __call__(self, account: Account):
        self.validate_no_child(account)
        self.validate_no_movements(account)
        account.delete()


class Account(MPTTModel):
    """ An Account, a tree structure to host movements. """
    #
    # Fields
    #
    name = NameField()
    acc_type = m.ForeignKey('AccountType', on_delete=m.CASCADE)
    parent = TreeForeignKey(
        'self',
        on_delete=m.PROTECT,
        null=True,
        blank=True,
        related_name="children"
    )

    #
    # Constants
    #
    ERR_MSGS: Dict[str, str] = {
        'NULL_PARENT': '`parent` can not be None.',
        'PARENT_CHILD_NOT_ALLOWED': 'Parent account {} does not allows children.'
    }

    #
    # Methods
    #
    def get_descendants_ids(
            self,
            include_self: bool,
            use_cache: bool = False
    ) -> List[int]:
        """ Returns the descendants ids, cached to avoid multiple queries """
        cache_key = (
            f"account_get_descendants_ids_pk={self.pk}_include_self={include_self}"
        )
        if use_cache is False or cache.get(cache_key) is None:
            qset = self\
                .get_descendants(include_self)\
                .values_list('pk', flat=True)
            cache.set(cache_key, [x for x in qset])
        return cache.get(cache_key)

    def get_name(self) -> str:
        return self.name

    def set_name(self, x: str) -> None:
        self.name = x
        full_clean_and_save(self)

    def get_parent(self) -> Account:
        """ Returns the parent. Can be None for the Root Account. """
        return self.parent

    def set_parent(self, parent: Account) -> None:
        if parent is None:
            msg = {'parent': self.ERR_MSGS['NULL_PARENT']}
            raise ValidationError(msg)
        if not parent.allows_children():
            msg = self.ERR_MSGS['PARENT_CHILD_NOT_ALLOWED']
            raise ValidationError({'parent': msg.format(parent)})
        self.parent = parent
        full_clean_and_save(self)

    def get_acc_type(self) -> AccTypeEnum:
        """ Getter for acc_type. Notice that instead of returning an
        AccountType objects, we return AccTypeEnum. This is because
        AccountType should only be known by this module. """
        return AccTypeEnum(self.acc_type.name)

    def allows_children(self) -> bool:
        """ Returns True if this account can be the parent of other accounts,
        else False"""
        return self.acc_type.children_allowed

    def count_children(self) -> int:
        """ Returns the number of children for this account """
        return self.get_descendant_count()

    def allows_movements(self) -> bool:
        """ Returns True if this account can have movements, else False """
        return self.acc_type.movements_allowed

    def count_movements(self) -> bool:
        """ Returns the number of movements for this account. """
        return self.movement_set.count()


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
def get_root_acc() -> Account:
    """ Returns the root account """
    return Account.objects.get(name="Root Account")


def get_currency_price_change_rebalance_acc() -> Account:
    """ Returns the account used to rebalance transactions on currency price
    changes """
    return Account.objects.get(name="Currency Price Change Compensation")
