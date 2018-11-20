import attr
from django.db.transaction import atomic
import django.db.models as m
from django.core.exceptions import ValidationError
from common.models import (
    NameField,
    new_price_field,
    full_clean_and_save,
    DECIMAL_PLACES
)
from accounts.models import get_currency_price_change_rebalance_acc


# ------------------------------------------------------------------------------
# Models
@attr.s()
class CurrencyFactory():
    """ Encapsulates creation of currencies """

    def __call__(self, name, base_price):
        """ Creates a currency using name and base_price """
        return full_clean_and_save(Currency(name=name, base_price=base_price))


class Currency(m.Model):

    ERR_MSGS = {
        "IMUTABLE_CURRENCY": "Currency {} is imutable."
    }

    #
    # Fields
    #
    name = NameField()
    base_price = new_price_field()
    imutable = m.BooleanField(default=False)

    #
    # Methods
    #
    @atomic
    def new_price_change(self, date_, new_price):
        """
        Register's a price change for a currency and returns.
        """
        from movements.models import Transaction
        rebalance_acc = get_currency_price_change_rebalance_acc()
        self._assert_not_imutable()
        price_change = full_clean_and_save(CurrencyPriceChange(
            date=date_,
            new_price=new_price.quantize(DECIMAL_PLACES),
            currency=self
        ))
        for trans in Transaction.objects.filter_affected_by_price_change(
                price_change
        ):
            trans.rebalance(rebalance_acc)
        return price_change

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

    def _assert_not_imutable(self):
        if self.imutable:
            m = self.ERR_MSGS['IMUTABLE_CURRENCY'].format(self.name)
            raise ValidationError(dict(price_change=m))


class CurrencyPriceChange(m.Model):
    """ The event of a change in a currency price """

    date = m.DateField()
    currency = m.ForeignKey(Currency, on_delete=m.CASCADE)
    new_price = new_price_field()

    class Meta:
        unique_together = ('date', 'currency')

    def get_currency(self):
        return self.currency

    def get_date(self):
        return self.date

    def has_next_price_change(self):
        return self.get_future_price_changes().exists()

    def get_next_price_change(self):
        return self.get_future_price_changes().first()

    def get_future_price_changes(self):
        """ Return an ordered queryset of price changes for the same currency
        after this one """
        return CurrencyPriceChange\
            .objects\
            .filter(currency=self.currency)\
            .filter(date__gt=self.date)\
            .order_by('date')


# ------------------------------------------------------------------------------
# Services
_cached_default_currency = None


def get_default_currency():
    """ Returns the default Currency. Cached for efficiency. """
    global _cached_default_currency
    if _cached_default_currency is None:
        _cached_default_currency = Currency.objects.get(name="Dollar")
    return _cached_default_currency
