""" Test factories for Currencies """
import factory as f
from faker import Faker

from currencies.models import Currency
from currencies.money import Money

# Custom faker w/ controlable seed
faker = Faker()
faker.seed(20139210)


class CurrencyTestFactory(f.DjangoModelFactory):
    class Meta:
        model = Currency

    name = f.Sequence(lambda n: faker.name())
    imutable = False


class MoneyTestFactory(f.Factory):
    class Meta:
        model = Money

    quantity = faker.pydecimal()
    currency = f.SubFactory(CurrencyTestFactory)
