import pytest
from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from accounts.management.commands.populate_accounts import (
    account_populator,
    account_type_populator,
)
from common.testutils import (
    URLS,
    DataMaker,
    TestHelpers,
    TestRequestMaker,
    TestRequests,
)
from currencies.management.commands.populate_currencies import currency_populator


@pytest.mark.functional
class MovementsFunctionalTests(StaticLiveServerTestCase):
    def setUp(self):
        super().setUpClass()
        account_type_populator()
        account_populator()
        currency_populator()
        self.requests = TestRequests(self.live_server_url)
        self.trm = TestRequestMaker(self.requests)
        self.root_acc = TestHelpers.find_root(self.trm.get_json(URLS.account))
        self.euro = TestHelpers.select_by(self.trm.get_currencies(), "name", "Euro")
        self.data_maker = DataMaker(self.root_acc)

    def test_deletes_a_transaction(self):
        # Creates a transaction
        supermarket_acc = self.trm.post_account(self.data_maker.supermarket_acc(self.root_acc))
        current_acc = self.trm.post_account(self.data_maker.current_acc(self.root_acc))
        supermarket_tra = self.trm.post_transaction(
            self.data_maker.paid_supermarket(current_acc, supermarket_acc, self.euro)
        )

        assert len(self.trm.get_transactions()) == 1

        self.trm.delete_transaction(supermarket_tra["pk"])

        assert len(self.trm.get_transactions()) == 0
