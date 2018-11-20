import attr
from decimal import Decimal
from common.models import DECIMAL_PLACES


@attr.s(frozen=True)
class Money():
    """ A combination of a quantity and a currency """
    quantity = attr.ib(convert=lambda x: Decimal(x).quantize(DECIMAL_PLACES))
    currency = attr.ib()
