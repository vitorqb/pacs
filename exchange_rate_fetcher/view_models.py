import attr


@attr.s(frozen=True)
class ExchangeRateDataInputs:
    start_at = attr.ib()
    end_at = attr.ib()
    currency_codes = attr.ib()
    token = attr.ib(default=None)
