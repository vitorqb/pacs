import exchangerates.models as models
import exchangerates.exceptions as exceptions
import collections
import datetime
import common.utils as utils


A_DAY = datetime.timedelta(days=1)


def fetch_exchange_rates(start_at, end_at, currency_codes):
    exchange_rates = models.ExchangeRate.objects.filter(
        currency_code__in=currency_codes,
        date__lte=end_at,
        date__gte=start_at,
    ).order_by('currency_code', 'date')
    prices = collections.defaultdict(dict)

    for exchange_rate in exchange_rates:
        prices[exchange_rate.currency_code][exchange_rate.date] = exchange_rate.value

    for date in utils.date_range(start_at, end_at):
        for currency_code in currency_codes:
            if prices[currency_code].get(date) is None:
                prev_day = date - A_DAY
                price = prices[currency_code].get(prev_day)
                if price is None:
                    raise exceptions.NotEnoughData(f"Missing data for date: {prev_day}")
                prices[currency_code][date] = price

    return [
        {
            "currency": currency_code,
            "prices": [
                {"date": date.strftime(utils.DATE_FORMAT), "price": float(prices[currency_code][date])}
                for date in sorted(prices[currency_code].keys())
            ]
        }
        for currency_code in currency_codes
    ]
