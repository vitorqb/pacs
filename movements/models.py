from decimal import Decimal
import attr
from pyrsistent import freeze, pvector, v

import django.db.models as m
from django.db.transaction import atomic
from rest_framework.exceptions import ValidationError

from common.models import full_clean_and_save, new_cents_field
from currencies.money import Money
from currencies.models import get_default_currency
from accounts.models import Account


@attr.s()
class TransactionFactory():
    """ Encapsulates the creation of Transactions and Movements """

    @atomic
    def __call__(self, description, date_, movements_specs):
        """ Creates a new Transaction. `movements_specs` should be a list
        of MovementSpec describing the movements for this transaction. """
        trans = full_clean_and_save(
            Transaction(description=description, date=date_)
        )
        trans.set_movements(movements_specs)
        return trans


class TransactionQuerySet(m.QuerySet):

    def filter_more_than_one_currency(self):
        """ Filters only by transactions that contain more than
        one currency """
        return self\
            .annotate(currency_count=m.Count('movement__currency', True))\
            .filter(currency_count__gt=1)

    def filter_by_currency(self, cur):
        """ Returns only transactions for which a movement uses a currency """
        return self.filter(movement__currency=cur)


class Transaction(m.Model):
    """
    A logical group of movements, representing money that is transfered out
    some accounts and in other accounts.
    Movements can only be created and manipulated via transactions.
    """
    ERR_MSGS = freeze({
        'SINGLE_ACCOUNT': "A Transaction can not have a single Account.",
        'UNBALANCED_SINGLE_CURRENCY': (
            "If all movements of a Transaction have a single currency, then"
            " the transaction must be balanced, having 0 value."
        ),
        'TWO_OR_MORE_MOVEMENTS': (
            "A transactions must have two or more movements."
        )
    })

    #
    # Fields
    #
    description = m.TextField()
    date = m.DateField()

    #
    # Django Magic
    #
    objects = TransactionQuerySet.as_manager()

    #
    # Methods
    #
    def get_description(self):
        return self.description

    def set_description(self, x):
        self.description = x
        full_clean_and_save(self)

    def get_date(self):
        return self.date

    def set_date(self, x):
        self.date = x
        full_clean_and_save(self)

    def get_movements_specs(self):
        """ Returns a list of MovementSpec with all movements for this
        transaction """
        movements = self.movement_set.all()
        return pvector(MovementSpec.from_movement(m) for m in movements)

    @atomic
    def set_movements(self, movements_specs):
        """ Set's movements, using an iterable of MovementSpec """
        self.movement_set.all().delete()
        self._validate_movements_specs(movements_specs)
        for mov_spec in movements_specs:
            self._convert_specs(mov_spec)
        full_clean_and_save(self)

    def _validate_movements_specs(self, movements_specs):
        def fail(msg):
            raise ValidationError({'movements_specs': msg})

        # At least 2 movements are needed
        if len(movements_specs) < 2:
            fail(self.ERR_MSGS['TWO_OR_MORE_MOVEMENTS'])

        # Single account is not allowed
        if len(set(x.account for x in movements_specs)) <= 1:
            return fail(self.ERR_MSGS['SINGLE_ACCOUNT'])

        # If movements have a single currency, the value must sum up to 0
        if len(set(x.money.currency for x in movements_specs)) == 1:
            value = sum(x.money.quantity for x in movements_specs)
            if value.quantize(Decimal(1)) != 0:
                fail(self.ERR_MSGS['UNBALANCED_SINGLE_CURRENCY'])

    def _convert_specs(self, mov_spec):
        """ Converts a MovementSpec into a Movement for self. """
        return full_clean_and_save(Movement(
            account=mov_spec.account,
            transaction=self,
            currency=mov_spec.money.currency,
            quantity=mov_spec.money.quantity
        ))


@attr.s(frozen=True)
class MovementSpec():
    """
    The specification for a movement. A Value-Object wrapper around Movement,
    used in it's creation.
    """
    account = attr.ib()

    @account.validator
    def _account_validator(self, attribute, account):
        if account.allows_movements() is False:
            m = "Account '{}' does not allow movements".format(account.name)
            raise ValidationError(m)

    money = attr.ib()

    @classmethod
    def from_movement(cls, mov):
        """ Creates a MovementSpec from a Movement """
        return MovementSpec(mov.get_account(), mov.get_money())


class MovementManager(m.Manager):

    def filter_currency(self, cur):
        return self.filter(currency=cur)


class Movement(m.Model):
    """
    A credit or debit of Money from an account.
    """

    #
    # Fields
    #
    account = m.ForeignKey(Account, on_delete=m.CASCADE)
    transaction = m.ForeignKey(Transaction, on_delete=m.CASCADE)
    # currency + quantity forms Money
    currency = m.ForeignKey('currencies.Currency', on_delete=m.CASCADE)
    quantity = new_cents_field()

    #
    # django magic
    #
    objects = MovementManager()

    #
    # Methods
    #
    def get_date(self):
        return self.transaction.get_date()

    def get_account(self):
        return self.account

    def get_transaction(self):
        return self.transaction

    def get_money(self):
        return Money(self.quantity, self.currency)
