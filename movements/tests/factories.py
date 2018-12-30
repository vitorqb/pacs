""" Test factories for Movements """
import factory as f
from django.db.models import QuerySet
from faker import Faker
from movements.models import (
    Movement, MovementSpec, Transaction, TransactionFactory
)
from accounts.tests.factories import AccountTestFactory
from currencies.tests.factories import MoneyTestFactory, CurrencyTestFactory
from common.models import list_to_queryset


# Custom faker w/ controlable seed
faker = Faker()
faker.seed(20139210)


class MovementSpecTestFactory(f.Factory):
    class Meta:
        model = MovementSpec

    account = f.SubFactory(AccountTestFactory)
    money = f.SubFactory(MoneyTestFactory)


class TransactionTestFactory(f.DjangoModelFactory):
    class Meta:
        model = Transaction

    description = faker.text()
    date_ = faker.date()
    movements_specs = f.List([
        f.SubFactory(MovementSpecTestFactory),
        f.SubFactory(MovementSpecTestFactory)
    ])

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return TransactionFactory()(*args, **kwargs)


class MovementTestFactory(f.DjangoModelFactory):
    class Meta:
        model = Movement

    account = f.SubFactory(AccountTestFactory)
    transaction = f.SubFactory(TransactionTestFactory)
    currency = f.SubFactory(CurrencyTestFactory)
    quantity = faker.pydecimal(left_digits=2)

    @classmethod
    def create_batch_qset(cls, n: int, *args, **kwargs) -> QuerySet:
        return list_to_queryset(cls.create_batch(n, *args, **kwargs))
