from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QScrollArea

from desktop_app import LineItemDialog, MainWindow, OverrideTotalDialog
from services.student_service import create_student
from utils import db


class DesktopUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_path = db.DATABASE_PATH
        self.old_url = db.DB_URL
        self.old_engine = db._engine
        self.old_session_local = db._SessionLocal

        db_path = Path(self.tmp.name) / "glass-ui-test.db"
        db.DATABASE_PATH = db_path
        db.DB_URL = f"sqlite:///{db_path}"
        db._engine = None
        db._SessionLocal = None
        db.init_db()

    def tearDown(self) -> None:
        if db._engine is not None:
            db._engine.dispose()
        db.DATABASE_PATH = self.old_path
        db.DB_URL = self.old_url
        db._engine = self.old_engine
        db._SessionLocal = self.old_session_local
        self.tmp.cleanup()

    def test_members_filter_and_scrollable_detail_panes(self) -> None:
        create_student({"student_id": "2024-0001", "name": "Member One"})
        create_student({"student_id": "2024-0002", "name": "Officer Role", "role_title": "Auditor"})
        create_student({"student_id": "2024-0003", "name": "Approver", "can_approve": True})

        window = MainWindow()
        self.addCleanup(window.close)

        members = window.members_tab
        self.assertEqual(len(members.table.all_rows), 3)
        members.officers_only.setChecked(True)

        officer_ids = {row["student_id"] for row in members.table.all_rows}
        self.assertEqual(officer_ids, {"2024-0002", "2024-0003"})
        self.assertGreaterEqual(len(window.findChildren(QScrollArea)), 5)

    def test_line_item_and_override_dialog_payloads(self) -> None:
        window = MainWindow()
        self.addCleanup(window.close)

        line_dialog = LineItemDialog(window)
        line_dialog.item_name.setText("Stapler")
        line_dialog.quantity.setValue(3)
        line_dialog.unit_cost.setValue(25)
        self.assertEqual(
            line_dialog.payload(),
            {
                "item_name": "Stapler",
                "quantity": 3,
                "unit_cost": 25.0,
                "line_total": 75.0,
            },
        )

        override_dialog = OverrideTotalDialog(
            window,
            computed_total=75,
            remaining_budget=100,
            current_amount=80,
            reason="Receipt total",
        )
        override_dialog.amount.setValue(80)
        override_dialog.reason.setText("Receipt total")
        self.assertEqual(override_dialog.payload(), (True, 80.0, "Receipt total"))

        override_dialog.amount.setValue(75)
        self.assertEqual(override_dialog.payload(), (False, 75.0, None))


if __name__ == "__main__":
    unittest.main()
