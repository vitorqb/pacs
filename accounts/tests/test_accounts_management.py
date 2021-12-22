from attr import evolve

from accounts.management.commands.populate_accounts import (
    account_populator,
    account_type_populator,
)
from accounts.models import AccountType
from common.testutils import PacsTestCase


class PopulateAccountTestCase(PacsTestCase):
    def setUp(self):
        super().setUp()
        self.acc_type_data = [
            {
                "name": "Root",
                "children_allowed": True,
                "movements_allowed": False,
                "new_accounts_allowed": False,
            }
        ]
        self.acc_type_populator = evolve(account_type_populator, model_data=self.acc_type_data)

        self.acc_data = [{"name": "Root Account", "acc_type_name": "Root", "parent_name": None}]
        self.acc_populator = evolve(account_populator, model_data=self.acc_data)

    def test_account_type_populator(self):
        self.acc_type_populator()
        assert len(self.acc_type_populator._created_objects) == 1
        obj = self.acc_type_populator._created_objects[0]
        assert obj.name == self.acc_type_data[0]["name"]
        assert obj.children_allowed == self.acc_type_data[0]["children_allowed"]
        assert obj.movements_allowed == self.acc_type_data[0]["movements_allowed"]
        assert obj.new_accounts_allowed == self.acc_type_data[0]["new_accounts_allowed"]

    def test_account_populator(self):
        self.acc_type_populator()
        self.acc_populator()
        assert len(self.acc_populator._created_objects) == 1
        acc = self.acc_populator._created_objects[0]
        assert acc.name == self.acc_data[0]["name"]
        assert acc.parent is None
        assert acc.acc_type == AccountType.objects.get(name=self.acc_data[0]["acc_type_name"])
