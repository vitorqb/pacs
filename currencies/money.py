import attr
from decimal import Decimal
from common.models import DECIMAL_PLACES


@attr.s(frozen=True)
class Money():
    """ A combination of a quantity and a currency """
    quantity = attr.ib(convert=lambda x: Decimal(x).quantize(DECIMAL_PLACES))
    currency = attr.ib()

    def get_value(self, date_):
        """ Get's the value for this money at a date """
        return self.quantity * self.currency.get_price(date_)

    def convert(self, new_currency, date_):
        """ Converts to a new currency using the prices at date_ """
        new_quantity = self.get_value(date_) / new_currency.get_price(date_)
        return attr.evolve(self, currency=new_currency, quantity=new_quantity)

    def revert(self):
        """ Returns self with the quantity's sign inverted """
        return attr.evolve(self, quantity=-self.quantity)
