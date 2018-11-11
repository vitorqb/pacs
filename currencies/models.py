import attr
import django.db.models as m
from common.models import NameField, PriceField, full_clean_and_save


# ------------------------------------------------------------------------------
# Models
@attr.s()
class CurrencyFactory():
    """ Encapsulates creation of currencies """

    def __call__(self, name, base_price):
        """ Creates a currency using name and base_price """
        return full_clean_and_save(Currency(name=name, base_price=base_price))


class Currency(m.Model):

    #
    # Fields
    #
    name = NameField()
    base_price = PriceField()
    imutable = m.BooleanField(default=False)

    #
    # Methods
    #
    def new_price_change(self, date_, new_price):
        """ Register's a price change for a currency and returns. """
        return full_clean_and_save(CurrencyPriceChange(
            date=date_,
            new_price=new_price,
            currency=self
        ))

    def get_price(self, date_):
        """ Returns price at a date """
        last_change = self.get_last_price_change_before(date_)
        if last_change is not None:
            return last_change.new_price
        return self.base_price

    def get_last_price_change_before(self, dt):
        """ Returns the last price change before date, inclusive. """
        return self\
            .currencypricechange_set\
            .all()\
            .order_by('-date')\
            .filter(date__lte=dt)\
            .first()

    def price_changes_iter(self):
        """ Returns an iterator through price changes in chronological
        order """
        yield from self.currencypricechange_set.all().order_by('date')

    def price_changes_iter_until(self, date_):
        """ Iterates through price changes until a date (included) """
        yield from self\
            .currencypricechange_set\
            .all()\
            .filter(date__lte=date_)\
            .order_by('date')


class CurrencyPriceChange(m.Model):
    """ The event of a change in a currency price """

    date = m.DateField()
    currency = m.ForeignKey(Currency, on_delete=m.CASCADE)
    new_price = PriceField()

    class Meta:
        unique_together = ('date', 'currency')


# ------------------------------------------------------------------------------
# Services
_cached_default_currency = None


def get_default_currency():
    """ Returns the default Currency. Cached for efficiency. """
    global _cached_default_currency
    if _cached_default_currency is None:
        _cached_default_currency = Currency.objects.get(name="Dollar")
    return _cached_default_currency
