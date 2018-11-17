import attr
from django.db.transaction import atomic
import django.db.models as m
from django.core.exceptions import ValidationError
from common.models import NameField, PriceField, full_clean_and_save, extract_pks
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
    base_price = PriceField()
    imutable = m.BooleanField(default=False)

    #
    # Methods
    #
    @atomic
    def new_price_change(self, date_, new_price):
        """
        Register's a price change for a currency and returns.
        """
        self._assert_not_imutable()
        price_change = full_clean_and_save(CurrencyPriceChange(
            date=date_,
            new_price=new_price,
            currency=self
        ))
        for trans in price_change.get_affected_transactions():
            trans.rebalance(get_currency_price_change_rebalance_acc())
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

    def get_movements(self):
        """ Returns a queryset of Movement with this currency """
        return self.movement_set.all()

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

    def _assert_not_imutable(self):
        if self.imutable:
            m = self.ERR_MSGS['IMUTABLE_CURRENCY'].format(self.name)
            raise ValidationError(dict(price_change=m))


class CurrencyPriceChange(m.Model):
    """ The event of a change in a currency price """

    date = m.DateField()
    currency = m.ForeignKey(Currency, on_delete=m.CASCADE)
    new_price = PriceField()

    class Meta:
        unique_together = ('date', 'currency')

    def get_currency(self):
        return self.currency

    def get_date(self):
        return self.date

    def has_next_price_change(self):
        return self.get_future_price_changes().exists()

    def get_next_price_chnage(self):
        return self.get_future_price_changes().first()

    def get_affected_transactions(self):
        """ Retrieves all transactions which have their values affected
        by this price change """
        # !!!! TODO -> Move to Transaction.objects
        from movements.models import Transaction
        movements_pks = extract_pks(self.currency.get_movements())
        next_price_change = self.get_future_price_changes().first()

        qset = Transaction.objects.all()
        qset = qset.filter(movement__pk__in=movements_pks)
        qset = qset.filter(date__gte=self.date)
        if next_price_change is not None:
            qset = qset.filter(date__lt=next_price_change.date)
        qset = qset.distinct()

        return qset

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
