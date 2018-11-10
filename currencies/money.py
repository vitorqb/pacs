import attr


@attr.s(frozen=True)
class Money():
    """ A combination of a quantity and a currency """
    currency = attr.ib()
    quantity = attr.ib()

    def change_currency(self, cur):
        """ Returns a new Money with a new currency """
        return attr.evolve(self, currency=cur)
