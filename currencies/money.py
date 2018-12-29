import attr
from decimal import Decimal
from .models import Currency
from common.utils import decimals_equal


@attr.s(frozen=True, cmp=False)
class Money():
    """ A combination of a quantity and a currency """
    quantity: Decimal = attr.ib(converter=Decimal)
    currency: Currency = attr.ib()

    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return False
        return (
            self.currency == other.currency and
            decimals_equal(self.quantity, other.quantity)
        )
