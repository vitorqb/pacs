import collections
import contextlib
import datetime
from decimal import Decimal

import attr
import django.db.utils

import common.utils as utils
import exchangerates.exceptions as exceptions
import exchangerates.models as models

A_DAY = datetime.timedelta(days=1)


def fetch_exchange_rates(start_at, end_at, currency_codes):
    exchange_rates = models.ExchangeRate.objects.filter(
        currency_code__in=currency_codes,
        date__lte=end_at,
        date__gte=start_at,
    ).order_by("currency_code", "date")
    prices = collections.defaultdict(dict)

    for exchange_rate in exchange_rates:
        prices[exchange_rate.currency_code][exchange_rate.date] = exchange_rate.value

    for date in utils.date_range(start_at, end_at):
        for currency_code in currency_codes:
            if prices[currency_code].get(date) is None:
                prev_day = date - A_DAY
                price = prices[currency_code].get(prev_day)
                if price is None:
                    raise exceptions.NotEnoughData(f"Missing data for {currency_code} {date}")
                prices[currency_code][date] = price

    return [
        {
            "currency": currency_code,
            "prices": [
                {
                    "date": date.strftime(utils.DATE_FORMAT),
                    "price": float(prices[currency_code][date]),
                }
                for date in sorted(prices[currency_code].keys())
            ],
        }
        for currency_code in currency_codes
    ]


@attr.s()
class ExchangeRateImportInput:
    currency_code = attr.ib()
    date_str = attr.ib()
    value_float = attr.ib()

    @classmethod
    def from_dict(cls, d):
        return cls(d["currency_code"], d["date"], d["value"])


@attr.s()
class ExchangeRateImportOptions:
    skip_existing = attr.ib(default=False)


def import_exchangerates(exchangerate_import_inputs, options=None):
    for exchangerate_import_input in exchangerate_import_inputs:
        with _handle_duplicated_exchangerates(options, exchangerate_import_input):
            import_exchangerate(exchangerate_import_input)


def import_exchangerate(exchangerate_import_input):
    model = models.ExchangeRate.objects.create(
        currency_code=exchangerate_import_input.currency_code,
        date=utils.str_to_date(exchangerate_import_input.date_str),
        value=utils.round_decimal(Decimal(exchangerate_import_input.value_float)),
    )
    model.full_clean()
    model.save()


@contextlib.contextmanager
def _handle_duplicated_exchangerates(options, exchangerate_import_input):
    try:
        yield
    except django.db.utils.IntegrityError as e:
        if "UNIQUE constraint failed" not in str(e):
            raise e
        if options and options.skip_existing is False:
            msg = f"Exchange rate already exists for {exchangerate_import_input}"
            raise exceptions.ExchangeRateAlreadyExists(msg) from e
