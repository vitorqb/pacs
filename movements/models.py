from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

import attr
import django.db.models as m
from django.db.transaction import atomic
from rest_framework.exceptions import ValidationError

from accounts.models import Account
from common.models import full_clean_and_save, new_money_quantity_field
from common.utils import round_decimal
from currencies.models import Currency
from currencies.money import Money

if TYPE_CHECKING:
    import datetime


@attr.s()
class TransactionFactory():
    """ Encapsulates the creation of Transactions (with Movements) """

    @atomic
    def __call__(
            self,
            description: str,
            date_: datetime.date,
            movements_specs: List[MovementSpec]
    ) -> Transaction:
        """ Creates a new Transaction. `movements_specs` should be a list
        of MovementSpec describing the movements for this transaction. """
        trans = full_clean_and_save(
            Transaction(description=description, date=date_)
        )
        trans.set_movements(movements_specs)
        return trans


class TransactionQuerySet(m.QuerySet):

    def filter_by_account(self, acc: Account) -> TransactionQuerySet:
        """ Returns only transactions for which a movement uses an account """
        acc_descendants_pks = list(
            acc.get_descendants(True).values_list('pk', flat=True)
        )
        return self.filter(movement__account__id__in=acc_descendants_pks)


class Transaction(m.Model):
    """
    A logical group of movements, representing money that is transfered out
    some accounts and in other accounts.
    Movements can only be created and manipulated via transactions.
    """
    ERR_MSGS: Dict[str, str] = {
        'SINGLE_ACCOUNT': "A Transaction can not have a single Account.",
        'UNBALANCED_SINGLE_CURRENCY': (
            "If all movements of a Transaction have a single currency, then"
            " the transaction must be balanced, having 0 value."
        ),
        'TWO_OR_MORE_MOVEMENTS': (
            "A transactions must have two or more movements."
        )
    }

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
    def get_description(self) -> str:
        return self.description

    def set_description(self, x: str) -> None:
        self.description = x
        full_clean_and_save(self)

    def get_date(self) -> datetime.date:
        return self.date

    def set_date(self, x: datetime.date) -> None:
        self.date = x
        full_clean_and_save(self)

    def get_movements_specs(self) -> List[MovementSpec]:
        """ Returns a list of MovementSpec with all movements for this
        transaction """
        movements = self.movement_set.all()
        return [MovementSpec.from_movement(m) for m in movements]

    def get_moneys_for_account(self, account: Account) -> List[Money]:
        """ Returns a list of Money object that represents the impact
        of this transaction for an account. """
        acc_descendants_pks = list(
            account.get_descendants(True).values_list("pk", flat=True)
        )
        return [
            x.money
            for x in self.get_movements_specs()
            if x.account.pk in acc_descendants_pks
        ]

    @atomic
    def set_movements(self, movements_specs: List[MovementSpec]) -> None:
        """ Set's movements, using an iterable of MovementSpec """
        self.movement_set.all().delete()
        self._validate_movements_specs(movements_specs)
        for mov_spec in movements_specs:
            self._convert_specs(mov_spec)
        full_clean_and_save(self)

    def _validate_movements_specs(
            self,
            movements_specs: List[MovementSpec]
    ) -> None:
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
            if round(value, 3) != 0:
                fail(self.ERR_MSGS['UNBALANCED_SINGLE_CURRENCY'])

        # !!! TODO -> add validation account can only appear once?

    def _convert_specs(self, mov_spec: MovementSpec) -> MovementSpec:
        """ Converts a MovementSpec into a Movement for self. """
        return full_clean_and_save(Movement(
            account=mov_spec.account,
            transaction=self,
            currency=mov_spec.money.currency,
            quantity=round_decimal(mov_spec.money.quantity)
        ))


@attr.s(frozen=True)
class MovementSpec():
    """
    The specification for a movement. A Value-Object wrapper around Movement,
    used in it's creation.
    """
    account: Account = attr.ib()
    money: Money = attr.ib()

    @account.validator
    def _account_validator(self, attribute, account):
        if account.allows_movements() is False:
            m = "Account '{}' does not allow movements".format(account.name)
            raise ValidationError(m)

    @classmethod
    def from_movement(cls, mov: Movement) -> MovementSpec:
        """ Creates a MovementSpec from a Movement """
        return MovementSpec(mov.get_account(), mov.get_money())


class MovementQueryset(m.QuerySet):
    pass


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
    currency = m.ForeignKey(Currency, on_delete=m.CASCADE)
    quantity = new_money_quantity_field()

    #
    # django magic
    #
    objects = MovementQueryset.as_manager()

    #
    # Methods
    #
    def get_date(self) -> datetime.date:
        return self.transaction.get_date()

    def get_account(self) -> Account:
        return self.account

    def get_transaction(self) -> Transaction:
        return self.transaction

    def get_money(self) -> Money:
        return Money(self.quantity, self.currency)
