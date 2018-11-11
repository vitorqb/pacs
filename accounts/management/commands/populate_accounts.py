import attr
from django.core.management import BaseCommand


class PopulateAccounts(BaseCommand):
    help = "Populates the Account and AccountType tables with default entires"

    def handle(self, *args, **kwargs):
        AccountTypePopulator()
        AccountPopulator()


# !!!! TODO
@attr.s()
class AccountTypePopulator():
    pass


@attr.s()
class AccountPopulator():
    pass
