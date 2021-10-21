from django.db import models
import common.models


class ExchangeRate(models.Model):
    currency_code = models.CharField(max_length=50)
    date = models.DateField()
    value = common.models.new_price_field()

    class Meta:
        indexes = [
            models.Index(fields=['currency_code']),
        ]
        unique_together = [['currency_code', 'date']]
