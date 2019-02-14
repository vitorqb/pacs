""" Test factories for Accounts """
import factory as f
from random import randint
from faker import Faker
from datetime import timedelta
A_DAY = timedelta(days=1)

from reports.reports import Period

# Custom faker w/ controlable seed
faker = Faker()
faker.seed(2013921)


class PeriodTestFactory(f.Factory):
    class Meta:
        model = Period

    start = f.LazyFunction(faker.date_object)
    end = f.LazyAttribute(lambda obj: obj.start + (randint(0, 60) * A_DAY))
