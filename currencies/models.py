import django.db.models as m
from django.core.validators import MinValueValidator
from common.models import NameField, CentsPriceField, full_clean_and_save


class Currency(m.Model):

    #
    # Fields
    #
    name = NameField()
    base_price = CentsPriceField()

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

    def price_changes_iter(self):
        """ Returns an iterator through price changes in chronological
        order """
        yield from self.currencypricechange_set.all().order_by('date')


class CurrencyPriceChange(m.Model):

    date = m.DateField()
    currency = m.ForeignKey(Currency, on_delete=m.CASCADE)
    new_price = CentsPriceField()

    class Meta:
        unique_together = ('date', 'currency')
