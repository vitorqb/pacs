from decimal import Decimal
from django.core.management import BaseCommand
from pyrsistent import m, v
from common.models import full_clean_and_save
from common.management import TablePopulator
from currencies.models import Currency


CURRENCIES_DATA = v(
    m(name="Dollar", base_price=1, imutable=True),
    m(name="Euro", base_price=Decimal('1.13')),
    m(name="Real", base_price=Decimal('0.27'))
)


currency_populator = TablePopulator(
    lambda x: full_clean_and_save(Currency(**x)),
    lambda x: Currency.objects.filter(name=x['name']).exists(),
    CURRENCIES_DATA
)


class Command(BaseCommand):
    help = "Populates the db with initial currencies"

    def handle(self, *args, **kwargs):
        currency_populator()
