import attr
from attr.validators import instance_of


@attr.s(frozen=True)
class Money():
    """ A combination of a quantity and a currency """
    quantity = attr.ib(validator=instance_of(int))
    currency = attr.ib()

    def get_value(self, date_):
        """ Get's the value for this money at a date """
        return int(round(self.quantity * self.currency.get_price(date_)))

    def convert(self, new_currency, date_):
        """ Converts to a new currency using the prices at date_ """
        value = self.get_value(date_)
        new_quantity = int(round(value / new_currency.get_price(date_)))
        return attr.evolve(self, currency=new_currency, quantity=new_quantity)
