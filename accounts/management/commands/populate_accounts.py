from django.core.management import BaseCommand
from common.management import TablePopulator
from accounts.models import Account, AccountType


ACCOUNT_TYPE_DATA = [
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
]


account_type_populator = TablePopulator(
    lambda x: AccountType.objects.create(**x),
    lambda x: AccountType.objects.filter(name=x['name']).exists(),
    ACCOUNT_TYPE_DATA,
)


ACCOUNT_DATA = [
    {'name': 'Root Account',
     'acc_type_name': 'Root',
     'parent_name': None},
]


def _populate_account(data):
    data = {**data}
    data['acc_type'] = AccountType.objects.get(name=data.pop('acc_type_name'))
    parent_name = data.pop('parent_name')
    data['parent'] = (
        None
        if parent_name is None else
        Account.objects.get(name=parent_name)
    )

    return Account.objects.create(**data)


account_populator = TablePopulator(
    _populate_account,
    lambda x: Account.objects.filter(name=x['name']).exists(),
    ACCOUNT_DATA
)


class Command(BaseCommand):
    help = "Populates the Account and AccountType tables with default entires"

    def handle(self, *args, **kwargs):
        account_type_populator()
        account_populator()
