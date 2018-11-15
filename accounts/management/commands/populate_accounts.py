from pyrsistent import freeze
from django.core.management import BaseCommand
from common.management import TablePopulator
from accounts.models import Account, AccountType


ACCOUNT_TYPE_DATA = freeze([
    {'name': "Root",
     'children_allowed': True,
     'movements_allowed': False,
     'new_accounts_allowed': False},
    {'name': "Branch",
     'children_allowed': True,
     'movements_allowed': False,
     'new_accounts_allowed': True},
    {'name': "Leaf",
     'children_allowed': False,
     'movements_allowed': True,
     'new_accounts_allowed': True},
])


account_type_populator = TablePopulator(
    lambda x: AccountType.objects.create(**x),
    lambda x: AccountType.objects.filter(name=x['name']).exists(),
    ACCOUNT_TYPE_DATA,
)


ACCOUNT_DATA = freeze([
    {'name': 'Root Account',
     'acc_type_name': 'Root',
     'parent_name': None},
    {'name': 'Currency Price Change Compensation',
     'acc_type_name': 'Leaf',
     'parent_name': 'Root Account'}
])


def _populate_account(data):
    acc_type = AccountType.objects.get(name=data['acc_type_name'])
    data = data.remove('acc_type_name').set('acc_type', acc_type)

    parent = (
        None
        if data['parent_name'] is None else
        Account.objects.get(name=data['parent_name'])
    )
    data = data.remove('parent_name').set('parent', parent)

    return Account.objects.create(**data)


account_populator = TablePopulator(
    _populate_account,
    lambda x: AccountType.objects.filter(name=x['name']).exists(),
    ACCOUNT_DATA
)


class PopulateAccounts(BaseCommand):
    help = "Populates the Account and AccountType tables with default entires"

    def handle(self, *args, **kwargs):
        account_type_populator()
        account_populator()
