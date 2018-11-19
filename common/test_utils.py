from decimal import Decimal
from pyrsistent import pmap, v, pvector
import attr
from itertools import count
from accounts.models import AccTypeEnum, get_root_acc, AccountFactory
from currencies.models import CurrencyFactory, get_default_currency
from currencies.money import Money
from movements.models import TransactionFactory, MovementSpec
from datetime import date


_account_name_generator = (f"_test_account_{i}" for i in count())


@attr.s()
class AccountBuilder():
    """ Facilitates creation of accounts for tests """

    # A callable that returns a name to use
    name_maker = attr.ib(default=lambda: next(_account_name_generator))

    # A AccTypeEnum to use
    acc_type_enum = attr.ib(default=AccTypeEnum.LEAF)

    # A callable that returns a default parent to use.
    parent_maker = attr.ib(default=get_root_acc)

    # An account factory to use
    acc_factory = attr.ib(factory=AccountFactory)

    def __call__(self, **kwargs):
        args_dct = self._prepare_args(pmap(kwargs))
        return self.acc_factory(**args_dct)

    def _prepare_args(self, initial_args):
        """ Returns a dictionary with all args needed to construct the account.
        Bases on initial_args, and set's all missing parameters. """
        return DictCompleter({
            'name': self.name_maker,
            'acc_type': lambda: self.acc_type_enum,
            'parent': self.parent_maker
        })(initial_args)


_currency_name_generator = (f"_test_currency_{i}" for i in count())


@attr.s()
class CurrencyBuilder():
    """ Facilitates the creation of currencies fort ests """

    # A callable that returns a valid currency name
    name_maker = attr.ib(default=lambda: next(_currency_name_generator))

    # A base_price to use
    base_price = attr.ib(default=Decimal('2.20'))

    # A CurrencyFactory to used
    currency_factory =  attr.ib(factory=CurrencyFactory)

    def __call__(self, **kwargs):
        args_dct = DictCompleter({
            'name': self.name_maker,
            'base_price': lambda: self.base_price
        })(kwargs)
        return self.currency_factory(**args_dct)


@attr.s()
class MovementSpecBuilder():
    """ Facilitates the creation of MovementSpecs for tests """

    # A callable that generates an account
    account_maker = attr.ib(factory=AccountBuilder)

    # A callable that produces a money
    money_maker = attr.ib(default=lambda: Money(100, get_default_currency()))

    def __call__(self, **kwargs):
        args_dct = DictCompleter({
            'account': self.account_maker,
            'money': self.money_maker
        })(kwargs)
        return MovementSpec(**args_dct)


@attr.s()
class TransactionBuilder():
    """ Facilitates the creation of transactions for tests """

    # A default description
    description = attr.ib(default="Test description")

    # A default date
    date = attr.ib(default=date(2017, 12, 24))

    # A callable returning balanced movement specs
    movements_specs_maker = attr.ib()

    # A TransactionFactory to use
    transaction_factory = attr.ib(factory=TransactionFactory)

    @movements_specs_maker.default
    def _movements_specs_maker_default(self, *args, **kwargs):
        accounts = [AccountBuilder()(), AccountBuilder()()]
        currencies = [CurrencyBuilder()(), CurrencyBuilder()()]
        base_money = Money(185, currencies[0])
        moneys = [
            base_money,
            base_money.convert(currencies[1], self.date).revert()
        ]
        return lambda: [MovementSpec(a, m) for a, m in zip(accounts, moneys)]

    def __call__(self, **kwargs):
        args_dct = self._prepare_args(pmap(kwargs))
        return self.transaction_factory(**args_dct)

    def _prepare_args(self, initial_args):
        if 'date' in initial_args:
            initial_args = initial_args\
                .set('date_', initial_args['date'])\
                .remove('date')
        return DictCompleter({
            'description': lambda: self.description,
            'date_': lambda: self.date,
            'movements_specs': self.movements_specs_maker
        })(initial_args)


@attr.s()
class DictCompleter:
    """ Completes a dictionary calling callables for missing keys """

    # A dictionary mapping keys -> callables.
    attrnm_callable_dct = attr.ib()

    def __call__(self, initial_args):
        args_dct = pmap(initial_args)
        missing = pvector(x for x in self.attrnm_callable_dct if x not in args_dct)
        for attrnm in missing:
            args_dct = args_dct.set(attrnm, self.attrnm_callable_dct[attrnm]())
        return args_dct
