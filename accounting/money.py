from __future__ import annotations
import attr
import typing
from decimal import Decimal
from common.utils import decimals_equal

if typing.TYPE_CHECKING:
    from currencies.models import Currency


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
