from django.core.management import BaseCommand
from pyrsistent import m, v, pvector
import attr
from common.models import full_clean_and_save
from currencies.models import Currency


CURRENCIES_DATA = v(
    m(name="Dollar", base_price=1, imutable=True),
    m(name="Euro", base_price=1.13),
    m(name="Real", base_price=0.27)
)


class Command(BaseCommand):
    help = "Populates the db with initial currencies"

    def handle(self, *args, **kwargs):
        CurrencyPopulator()()


@attr.s()
class CurrencyPopulator():

    # A function used to print
    _printfun = attr.ib(default=print)

    # What to create
    _currencies_data = attr.ib(default=CURRENCIES_DATA)

    # Stores created currencies
    _created_currencies = attr.ib(factory=v, init=False)

    def __call__(self):
        """ Populates the db, creating all uncreated currencies """
        self._printfun("Creating currencies... ", end="")
        currencies_to_create = pvector(
            x for x in self._currencies_data if not self._currency_exists(x)
        )
        for cur_data in currencies_to_create:
            self._created_currencies += [self._create_currency(cur_data)]
        self._printfun(
            f"Created currencies: {[x.name for x in self._created_currencies]}"
        )

    def _currency_exists(self, cur_data):
        return Currency.objects.filter(name=cur_data['name']).exists()

    def _create_currency(self, cur_data):
        """ The only place that allowed to skip the Factory """
        return full_clean_and_save(Currency(**cur_data))
