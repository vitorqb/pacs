from datetime import date
from decimal import Decimal
from copy import copy

from rest_framework.serializers import DateField

from accounts.management.commands.populate_accounts import (account_populator,
                                                            account_type_populator)
from accounts.models import AccTypeEnum
from accounts.tests.factories import AccountTestFactory
from common.testutils import PacsTestCase
from currencies.money import Money
from currencies.serializers import MoneySerializer
from currencies.tests.factories import CurrencyTestFactory, MoneyTestFactory
from movements.models import MovementSpec, TransactionFactory
from movements.serializers import MovementSpecSerializer, TransactionSerializer, TransactionTagSerializer
from movements.tests.factories import TransactionTestFactory


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

    def test_create_with_comment(self):
        comment = "FOO"
        self.data['comment'] = comment
        assert self.create() == MovementSpec(self.acc, self.money, comment)


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

    def test_serialize_base(self):
        trans = TransactionTestFactory(reference="foo")
        ser = TransactionSerializer(trans)
        assert ser.data == {
            'pk': trans.pk,
            'description': trans.get_description(),
            'date': DateField().to_representation(trans.get_date()),
            'reference': trans.get_reference(),
            'movements_specs': [
                MovementSpecSerializer(m).data for m in trans.get_movements_specs()
            ],
            'tags': [
                TransactionTagSerializer(m).data for m in trans.get_tags()
            ]
        }

    def test_from_data_base(self):
        trans = self.create()
        assert trans.get_description() == self.data['description']
        assert trans.get_date() == self.data['date']
        movements = trans.get_movements_specs()
        assert movements == [
            MovementSpec(self.accs[0], Money(10, self.curs[0])),
            MovementSpec(self.accs[1], Money(-8, self.curs[1])),
        ]

    def test_create_with_reference(self):
        self.data['reference'] = 'FOO'
        trans = self.create()
        assert trans.get_description() == self.data['description']
        assert trans.get_date() == self.data['date']
        assert trans.get_reference() == self.data['reference']

    def test_update_description(self):
        obj = self.create()

        self.data['description'] = 'Alohasdsa'
        new_obj = self.update(obj)

        assert new_obj.pk == obj.pk
        assert new_obj.get_description() == self.data['description']

    def test_update_reference(self):
        self.data['reference'] = 'FOO'
        trans = self.create()
        self.data['reference'] = 'BAR'

        new_trans = self.update(trans)

        assert new_trans.pk == trans.pk
        assert new_trans.get_reference() == 'BAR'

    def test_update_reference_null(self):
        self.data['reference'] = 'FOO'
        trans = self.create()
        self.data['reference'] = None
        new_trans = self.update(trans)
        assert new_trans.get_reference() == None

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
