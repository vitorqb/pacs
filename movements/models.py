from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Dict, List, NoReturn

import attr
import django.db.models as m
from django.db.transaction import atomic
from rest_framework.exceptions import ValidationError

from accounts.models import Account
from common.models import full_clean_and_save, new_money_quantity_field
from common.utils import round_decimal, decimals_equal
from currencies.models import Currency
from currencies.money import Money, Balance

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
            movements_specs: List[MovementSpec],
            reference: str = None,
    ) -> Transaction:
        """ Creates a new Transaction. `movements_specs` should be a list
        of MovementSpec describing the movements for this transaction. """
        trans = full_clean_and_save(
            Transaction(description=description, date=date_, reference=reference)
        )
        trans.set_movements(movements_specs)
        return trans


class TransactionQuerySet(m.QuerySet):

    def filter_by_account(self, acc: Account) -> TransactionQuerySet:
        """ Returns only transactions for which a movement uses an account """
        acc_descendants_pks = acc.get_descendants_ids(True, True)
        return self.filter(movement__account__id__in=acc_descendants_pks)

    def filter_before_transaction(
            self,
            transaction: Transaction
    ) -> TransactionQuerySet:
        """ Filters itself to only consider transactions before another transaction,
        considering an ordering of (date, id) """
        date_ = transaction.get_date()
        pk = transaction.pk

        x = self.order_by('date', 'pk')
        x = x.filter(m.Q(date__lt=date_) | m.Q(date=date_, pk__lt=pk))
        return x

    def get_balance_for_account(self, account: Account) -> Balance:
        """ Returns the Moneys for an account considering all transactions,
        in an efficient way. """
        movements = self.filter_by_account(account)._get_movements_qset().distinct()
        data_dct = (
            movements
            .values("currency_id")                   # Group by currency
            .annotate(quantity=m.Sum("quantity"))    # Sum value
        )
        return Balance([
            Money(x['quantity'], Currency.objects.get(id=x['currency_id']))
            for x in data_dct
        ])

    def _get_movements_qset(self):
        """ Returns a queryset of all Movements related to self (distincted) """
        pks = self.values_list('movement__pk', flat=True)
        return Movement.objects.filter(pk__in=pks)


class Transaction(m.Model):
    """
    A logical group of movements, representing money that is transfered out
    some accounts and in other accounts.
    Movements can only be created and manipulated via transactions.
    """

    #
    # Fields
    #
    # !!!! TODO -> Add comments field (large texts for detailed comments)
    description = m.TextField()
    reference = m.CharField(max_length=120, blank=True, null=True)
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

    def get_reference(self) -> str:
        return self.reference

    def set_description(self, x: str) -> None:
        self.description = x
        full_clean_and_save(self)

    def set_reference(self, x: str) -> None:
        self.reference = x
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

    def get_balance_for_account(self, account: Account) -> Balance:
        """ Returns a list of Money object that represents the impact
        of this transaction for an account. """
        acc_descendants_pks = account.get_descendants_ids(True, True)
        return Balance([
            x.money
            for x in self.get_movements_specs()
            if x.account.pk in acc_descendants_pks
        ])

    # !!!! TODO -> rename to set_movements_specs
    @atomic
    def set_movements(self, movements_specs: List[MovementSpec]) -> None:
        """ Set's movements, using an iterable of MovementSpec """
        TransactionMovementSpecListValidator().validate(movements_specs)
        self.movement_set.all().delete()
        for mov_spec in movements_specs:
            self._convert_specs(mov_spec)
        full_clean_and_save(self)

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
    account = m.ForeignKey(Account, on_delete=m.PROTECT)
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


#
# Auxiliary classes
#
class TransactionMovementSpecListValidator:
    """ Auxiliar class to validate a list of movement specs for a Transaction """

    ERR_MSGS: Dict[str, str] = {
        'SINGLE_ACCOUNT': "A Transaction can not have a single Account.",
        'UNBALANCED_SINGLE_CURRENCY': (
            "If all movements of a Transaction have a single currency, then"
            " the transaction must be balanced, having 0 value."
        ),
        'TWO_OR_MORE_MOVEMENTS': (
            "A transactions must have two or more movements."
        ),
        'REPEATED_CURRENCY_ACCOUNT_PAIR': (
            "There can NOT be two movements with the same (account, currency) pair"
        )
    }

    def fail(self, key: str) -> NoReturn:
        raise ValidationError({'movements_specs': self.ERR_MSGS[key]})

    def validate(self, movement_specs: List[MovementSpec]) -> None:
        currency_set = set(x.money.currency for x in movement_specs)
        account_set = set(x.account for x in movement_specs)
        account_currency_pair_set = set(
            (x.money.currency, x.account) for x in movement_specs
        )

        if len(movement_specs) < 2:
            self.fail("TWO_OR_MORE_MOVEMENTS")

        if len(account_set) == 1:
            self.fail("SINGLE_ACCOUNT")

        if len(currency_set) == 1:
            value = sum(x.money.quantity for x in movement_specs)
            if not decimals_equal(value, Decimal(0)):
                self.fail("UNBALANCED_SINGLE_CURRENCY")

        # Each pair (account, currency) should only appear once
        if len(account_currency_pair_set) < len(movement_specs):
            self.fail('REPEATED_CURRENCY_ACCOUNT_PAIR')
