import django.db.models as m
from common.models import NameField, CentsField


class Currency(m.Model):
    """ Represents a currency """

    #
    # Fields
    #
    name = NameField()
    base_price = CentsField()
