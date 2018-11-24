""" Test factories for Accounts """
import factory as f
from faker import Faker
from accounts.models import Account, AccountType, get_root_acc


# Custom faker w/ controlable seed
faker = Faker()
faker.seed(2013921)


class AccountTestFactory(f.DjangoModelFactory):
    class Meta:
        model = Account

    name = f.Sequence(lambda *a: faker.name())
    acc_type = f.LazyAttribute(lambda *a: AccountType.objects.get(name='Leaf'))
    parent = f.LazyAttribute(lambda *a: get_root_acc())
