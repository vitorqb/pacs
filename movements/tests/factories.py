""" Test factories for Movements """
import factory as f
from faker import Faker
from movements.models import MovementSpec
from accounts.tests.factories import AccountTestFactory
from currencies.tests.factories import MoneyTestFactory


# Custom faker w/ controlable seed
faker = Faker()
faker.seed(20139210)


class MovementSpecTestFactory(f.Factory):
    class Meta:
        model = MovementSpec

    account = f.SubFactory(AccountTestFactory)
    money = f.SubFactory(MoneyTestFactory)
