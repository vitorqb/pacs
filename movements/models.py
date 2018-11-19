from decimal import Decimal
import attr
from pyrsistent import freeze, v
import django.db.models as m
from django.db.transaction import atomic
from django.core.exceptions import ValidationError
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

    def filter_affected_by_price_change(self, price_change):
        """ Filters all transactions that were affected by a price change.
        Affected means that their values depend on that price change. """
        qset = self\
            .filter_more_than_one_currency()\
            .filter_by_currency(price_change.get_currency())\
            .filter(date__gte=price_change.get_date())
        if price_change.has_next_price_change():
            qset = qset.filter(date__lt=price_change.get_next_price_change().date)
        return qset

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
    A group of Movements whose values sums up to 0.
    Movements can only be created and manipulated via transactions.
    """
    ERR_MSGS = freeze({
        'UNBALANCED_MOVEMENTS': "Movements in Transaction don't sum up to 0.",
        'SINGLE_ACCOUNT': "A Transaction can not have a single Account."
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

    def get_date(self):
        return self.date

    def get_movements(self):
        """ Returns a queryset with all movements for this transaction """
        return self.movement_set.all()

    @atomic
    def set_movements(self, movements_specs):
        """ Set's movements, using an iterable of MovementSpec """
        self.movement_set.all().delete()
        self._validate_movements_specs(movements_specs)
        for mov_spec in movements_specs:
            self._convert_specs(mov_spec)
        full_clean_and_save(self)

    def rebalance(self, rebalancing_account):
        """ Rebalances the transaction, creating a new movement for
        `rebalancing_account` that forces the value of the transaction
        to be zero. Usually called when a new price change is created
        that changes the value of this transaction """
        value = sum(x.get_money().get_value(self.date) for x in self.get_movements())
        if value.quantize(Decimal(1)) == 0:
            return
        money = Money(value, get_default_currency()).revert()
        mov_spec = MovementSpec(rebalancing_account, money)
        self._convert_specs(mov_spec)
        full_clean_and_save(self)

    def _validate_movements_specs(self, movements_specs):
        value = sum(x.get_value(self.date) for x in movements_specs)
        if not value.quantize(Decimal(1)) == 0:
            raise ValidationError(self.ERR_MSGS['UNBALANCED_MOVEMENTS'])
        if len(set(x.account for x in movements_specs)) <= 1:
            raise ValidationError(self.ERR_MSGS['SINGLE_ACCOUNT'])

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
            return ValidationError(m)

    money = attr.ib()

    def get_value(self, date_):
        return self.money.get_value(date_)


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
