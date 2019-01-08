from datetime import date
from decimal import Decimal

from common.test import PacsTestCase

from movements.serializers import TransactionSerializer, MovementSpecSerializer
from movements.models import MovementSpec, Movement
from accounts.tests.factories import AccountTestFactory
from accounts.models import AccountType, AccTypeEnum
from accounts.management.commands.populate_accounts import (
    account_type_populator,
    account_populator
)
from currencies.tests.factories import CurrencyTestFactory, MoneyTestFactory
from accounting.money import Money
from currencies.serializers import MoneySerializer


class MovementsSerializersTestCase(PacsTestCase):
    def setUp(self):
        super().setUp()
        account_type_populator()
        account_populator()


class TestMovementSpecSerializer(MovementsSerializersTestCase):

    def setUp(self):
        super().setUp()
        self.acc = AccountTestFactory(acc_type=AccTypeEnum.LEAF)
        self.money = MoneyTestFactory()
        self.data = {
            "account": self.acc.pk,
            "money": MoneySerializer(self.money).data
        }

    def create(self):
        """ Creates using the serializer and self.data """
        ser = MovementSpecSerializer(data=self.data)
        ser.is_valid(True)
        return ser.save()

    def test_create_base(self):
        assert self.create() == MovementSpec(self.acc, self.money)


class TransactionSerializerTest(MovementsSerializersTestCase):

    def setUp(self):
        super().setUp()
        self.accs = AccountTestFactory.create_batch(
            3,
            acc_type=AccTypeEnum.LEAF
        )
        self.curs = CurrencyTestFactory.create_batch(2)
        self.moneys = [
            Money(10, self.curs[0]),
            Money(-8, self.curs[1])
        ]
        self.movements_specs = [
            MovementSpec(self.accs[0], self.moneys[0]),
            MovementSpec(self.accs[1], self.moneys[1])
        ]
        self.data = {
            'description': 'hola',
            'date': date(1993, 11, 23),
            'movements_specs': [
                MovementSpecSerializer(self.movements_specs[0]).data,
                MovementSpecSerializer(self.movements_specs[1]).data
            ]
        }

    def create(self):
        """ Uses the serializer to create with self.data """
        ser = TransactionSerializer(data=self.data)
        ser.is_valid(True)
        return ser.save()

    def update(self, obj):
        """ Uses the serializer to update with self.data """
        ser = TransactionSerializer(obj, data=self.data)
        ser.is_valid(True)
        return ser.save()

    def test_from_data_base(self):
        trans = self.create()
        assert trans.get_description() == self.data['description']
        assert trans.get_date() == self.data['date']
        movements = trans.get_movements_specs()
        assert movements == [
            MovementSpec(self.accs[0], Money(10, self.curs[0])),
            MovementSpec(self.accs[1], Money(-8, self.curs[1])),
        ]

    def test_update_description(self):
        obj = self.create()

        self.data['description'] = 'Alohasdsa'
        new_obj = self.update(obj)

        assert new_obj.pk == obj.pk
        assert new_obj.get_description() == self.data['description']

    def test_update_movements_specs(self):
        obj = self.create()

        self.data['movements_specs'][0]['money']['currency'] = self.curs[1].pk
        self.data['movements_specs'][1]['money']['currency'] = self.curs[1].pk
        self.data['movements_specs'][0]['money']['quantity'] = Decimal(100)
        self.data['movements_specs'][1]['money']['quantity'] = Decimal(-100)

        new_obj = self.update(obj)
        movements = new_obj.get_movements_specs()
        assert all(mov.money.currency == self.curs[1] for mov in movements)
        assert [mov.money.quantity for mov in movements] == \
            [Decimal(100), Decimal(-100)]

    def test_update_date(self):
        obj = self.create()
        self.data['date'] = date(1991, 9, 13)
        assert obj.get_date() != self.data['date']
        new_obj = self.update(obj)
        assert new_obj.get_date() == self.data['date']
