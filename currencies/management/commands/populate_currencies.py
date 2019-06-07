from django.core.management import BaseCommand

from common.management import TablePopulator
from common.models import full_clean_and_save
from currencies.models import Currency

CURRENCIES_DATA = [
    dict(name="Dollar", code='USD', imutable=True),
    dict(name="Euro", code='EUR'),
    dict(name="Real", code='BRL'),
]


currency_populator = TablePopulator(
    lambda x: full_clean_and_save(Currency(**x)),
    lambda x: Currency.objects.filter(name=x['name']).exists(),
    CURRENCIES_DATA
)


class Command(BaseCommand):
    help = "Populates the db with initial currencies"

    def handle(self, *args, **kwargs):
        currency_populator()
