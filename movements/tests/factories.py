""" Test factories for Movements """
import factory as f
from django.db.models import QuerySet
from faker import Faker

from accounts.tests.factories import AccountTestFactory
from common.models import list_to_queryset
from currencies.tests.factories import CurrencyTestFactory, MoneyTestFactory
from movements.models import (Movement, MovementSpec, Transaction,
                              TransactionFactory, TransactionTag)

# Custom faker w/ controlable seed
faker = Faker()
Faker.seed(20139210)


class MovementSpecTestFactory(f.Factory):
    class Meta:
        model = MovementSpec

    account = f.SubFactory(AccountTestFactory)
    money = f.SubFactory(MoneyTestFactory)


class TransactionTagFactory(f.DjangoModelFactory):
    name = f.LazyFunction(lambda: faker.text().split(' ')[0])
    value = f.LazyFunction(lambda: faker.text().split(' ')[0])

    class Meta:
        model = TransactionTag


class TransactionTestFactory(f.DjangoModelFactory):
    class Meta:
        model = Transaction

    description = f.LazyFunction(faker.text)
    date_ = f.LazyFunction(faker.date)
    movements_specs = f.List([
        f.SubFactory(MovementSpecTestFactory),
        f.SubFactory(MovementSpecTestFactory)
    ])
    tags = f.RelatedFactoryList(TransactionTagFactory, 'transaction')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return TransactionFactory()(*args, **kwargs)


class MovementTestFactory(f.DjangoModelFactory):
    class Meta:
        model = Movement

    account = f.SubFactory(AccountTestFactory)
    transaction = f.SubFactory(TransactionTestFactory)
    currency = f.SubFactory(CurrencyTestFactory)
    quantity = f.LazyFunction(lambda: faker.pydecimal(left_digits=2))

    @classmethod
    def create_batch_qset(cls, n: int, *args, **kwargs) -> QuerySet:
        return list_to_queryset(cls.create_batch(n, *args, **kwargs))
