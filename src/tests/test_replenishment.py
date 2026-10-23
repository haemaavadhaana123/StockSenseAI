"""Isolated regression checks; no test writes to the application's data directory."""

from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from utils import workflow_storage as storage
from utils.replenishment import (
    create_replenishment_requests,
    load_recommendations,
)


ROOT = Path(__file__).resolve().parents[1]


class ReplenishmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        shutil.copy2(ROOT / "data/sample_inventory.csv", directory / "inventory.csv")
        for key, value in {
            "DATA_DIR": directory,
            "INVENTORY_FILE": directory / "inventory.csv",
            "REQUESTS_FILE": directory / "requests.csv",
            "ACTIVITY_FILE": directory / "activity.csv",
        }.items():
            patcher = patch.object(storage, key, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        storage.ensure_workflow_files()

    def change_stock(self, value):
        inventory = pd.read_csv(storage.INVENTORY_FILE)
        inventory["current_stock"] = inventory["current_stock"].astype(float)
        inventory.loc[inventory.product_id == "P003", "current_stock"] = value
        inventory.to_csv(storage.INVENTORY_FILE, index=False)

    def test_whole_number_requests_and_logs(self):
        self.assertEqual(create_replenishment_requests(["P003", "P004"]), 2)
        requests = storage.load_requests()
        self.assertEqual(
            dict(zip(requests.product_id, requests.proposed_quantity)),
            {"P003": 45, "P004": 30},
        )
        self.assertEqual(set(requests.status), {"Pending"})
        self.assertEqual(requests.request_id.nunique(), 2)
        self.assertEqual(
            set(storage.load_activity().request_id), set(requests.request_id)
        )

    def test_fractional_quantity_matches_recommendation(self):
        self.change_stock(5.5)
        recommended = load_recommendations().set_index("product_id").loc[
            "P003", "proposed_quantity"
        ]
        create_replenishment_requests(["P003"])
        self.assertEqual(recommended, 44.5)
        self.assertEqual(storage.load_requests().iloc[0].proposed_quantity, recommended)
        self.assertIn("44.5 kg", storage.load_activity().iloc[0].details)

    def test_small_fraction_not_discarded(self):
        inventory = pd.read_csv(storage.INVENTORY_FILE)
        for column in ("current_stock", "minimum_stock", "target_stock"):
            inventory[column] = inventory[column].astype(float)
        inventory.loc[
            inventory.product_id == "P003",
            ["current_stock", "minimum_stock", "target_stock"],
        ] = [0.2, 0.3, 0.3]
        inventory.to_csv(storage.INVENTORY_FILE, index=False)
        create_replenishment_requests(["P003"])
        self.assertEqual(storage.load_requests().iloc[0].proposed_quantity, 0.1)

    def test_invalid_and_duplicate_selections_do_not_write(self):
        for selected in ([], ["UNKNOWN"], ["P001"]):
            with self.assertRaises(ValueError):
                create_replenishment_requests(selected)
        self.assertTrue(storage.load_requests().empty)
        self.assertTrue(storage.load_activity().empty)
        create_replenishment_requests(["P003", "P003"])
        with self.assertRaisesRegex(ValueError, "pending request"):
            create_replenishment_requests(["P003"])
        self.assertEqual(len(storage.load_requests()), 1)
        self.assertEqual(len(storage.load_activity()), 1)

    def test_nonfinite_stock_excluded(self):
        self.change_stock(float("inf"))
        self.assertNotIn("P003", set(load_recommendations().product_id))

    def test_no_recommendations_state(self):
        inventory = pd.read_csv(storage.INVENTORY_FILE)
        inventory["current_stock"] = inventory["target_stock"]
        inventory.to_csv(storage.INVENTORY_FILE, index=False)
        self.assertTrue(load_recommendations().empty)
        page = AppTest.from_file(
            str(ROOT / "pages/replenishment.py"), default_timeout=20
        ).run()
        self.assertFalse(page.exception)
        self.assertTrue(page.success)
        self.assertEqual(len(page.multiselect), 0)

    def test_fractional_request_integrates_with_approval(self):
        self.change_stock(5.5)
        inventory_before = storage.INVENTORY_FILE.read_bytes()
        create_replenishment_requests(["P003"])
        request_id = str(storage.load_requests().iloc[0].request_id)
        storage.decide_request(request_id, "Approved", decision_reason="Reviewed")
        storage.submit_to_simulated_procurement(request_id)
        request = storage.load_requests().iloc[0]
        self.assertEqual(request.proposed_quantity, 44.5)
        self.assertEqual(request.status, "Submitted to Simulated Procurement")
        self.assertEqual(len(storage.load_activity()), 3)
        self.assertEqual(storage.INVENTORY_FILE.read_bytes(), inventory_before)

    def check_page(self, filename, main=False):
        self.change_stock(5.5)
        page = AppTest.from_file(str(ROOT / filename), default_timeout=20).run()
        if main:
            page.sidebar.radio[0].set_value("Replenishment Recommendations").run()
        self.assertFalse(page.exception, [error.message for error in page.exception])
        next(b for b in page.button if b.label == "Create simulated requests").click().run()
        self.assertTrue(page.warning)
        page.multiselect[0].set_value(["P003"])
        next(b for b in page.button if b.label == "Create simulated requests").click().run()
        self.assertFalse(page.exception, [error.message for error in page.exception])
        self.assertEqual(storage.load_requests().iloc[0].proposed_quantity, 44.5)
        self.assertEqual(len(storage.load_activity()), 1)
        self.assertTrue(page.success)
        page.run()
        self.assertNotIn("P003", page.multiselect[0].value)
        self.assertEqual(len(storage.load_requests()), 1)
        if main:
            page.sidebar.radio[0].set_value("Dashboard").run()
            page.sidebar.radio[0].set_value("Replenishment Recommendations").run()
            self.assertFalse(page.exception)
            self.assertEqual(len(storage.load_requests()), 1)

    def test_main_screen(self):
        self.check_page("app.py", main=True)

    def test_standalone_page(self):
        self.check_page("pages/replenishment.py")


if __name__ == "__main__":
    unittest.main()
