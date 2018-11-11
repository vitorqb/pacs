import attr
import django.db.models as m
from mptt.models import MPTTModel, TreeForeignKey
from common.models import NameField


@attr.s()
class AccountFactory():
    """ Encapsulates the creation of Account """
    pass


# !!!! TODO -> Add population of Account
class Account(MPTTModel):
    """ An Account, a tree structure to host transactions. """
    name = NameField()
    acc_type = m.ForeignKey('AccountType')
    parent = TreeForeignKey(
        'self',
        on_delete=m.CASCADE,
        null=True,
        blank=True,
        related_name="children"
    )


# !!!! TODO -> Add population of AccountType
class AccountType(m.Model):
    """ A possible account type """
    name = NameField()
    children_allowed = m.BooleanField()
    movements_allowed = m.BooleanField()
    new_accounts_allowed = m.BooleanField()
