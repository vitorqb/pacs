""" Test factories for Accounts """
from datetime import timedelta
from random import randint

import factory as f
from faker import Faker

A_DAY = timedelta(days=1)

from reports.reports import Period

# Custom faker w/ controlable seed
faker = Faker()
Faker.seed(2013921)


class PeriodTestFactory(f.Factory):
    class Meta:
        model = Period

    start = f.LazyFunction(faker.date_object)
    end = f.LazyAttribute(lambda obj: obj.start + (randint(0, 60) * A_DAY))
