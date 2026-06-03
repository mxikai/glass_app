from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.services.budget_service import (
    create_budget_item,
    create_budget_plan,
    create_fund_bucket,
    delete_budget_item,
)
from backend.services.inventory_service import (
    create_inventory_item,
    delete_inventory_item,
    list_inventory_items,
)
from backend.services.student_service import create_student, delete_student
from backend.services.transaction_service import create_transaction, delete_transaction
from backend.utils import db
from backend.utils.validators import academic_year_value, iso_date_value, student_id_value


class IsolatedDatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.old_path = db.DATABASE_PATH
        self.old_url = db.DB_URL
        self.old_engine = db._engine
        self.old_session_local = db._SessionLocal

        db_path = Path(self.tmp.name) / "glass-test.db"
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

    def seed_plan(self) -> dict:
        create_student(
            {
                "student_id": "2024-0001",
                "name": "Alex Rivera",
                "program": "BSCS",
                "year_level": 2,
                "can_approve": True,
            }
        )
        create_student({"student_id": "2024-0002", "name": "Bea Santos"})
        return create_budget_plan(
            {
                "academic_year": "2025-2026",
                "semester": "1st",
                "total_planned_budget": 1000,
                "member_count": 2,
                "student_ids": ["2024-0001", "2024-0002"],
            }
        )

    def seed_item(self, plan_id: int) -> dict:
        bucket = create_fund_bucket(
            {
                "plan_id": plan_id,
                "bucket_name": "Operations",
                "planned_amount": 600,
            }
        )
        return create_budget_item(
            {
                "bucket_id": bucket["bucket_id"],
                "item_name": "Supplies",
                "planned_amount": 300,
            }
        )


class ValidatorTests(IsolatedDatabaseTestCase):
    def test_student_id_format_is_exact(self) -> None:
        self.assertEqual(student_id_value("2024-0001"), "2024-0001")
        for value in ["2024-00001", "2024-001", "S-1001", "2024-ABCD", "20240001"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    student_id_value(value)

    def test_academic_year_and_future_date_validation(self) -> None:
        self.assertEqual(academic_year_value("2025-2026"), "2025-2026")
        with self.assertRaises(ValueError):
            academic_year_value("2025-2027")
        with self.assertRaises(ValueError):
            iso_date_value(date.today() + timedelta(days=1), "approved_date", no_future=True)


class ServiceValidationTests(IsolatedDatabaseTestCase):
    def test_create_student_rejects_bad_student_id(self) -> None:
        with self.assertRaises(ValueError):
            create_student({"student_id": "S-1001", "name": "Old Seed"})

    def test_payment_student_must_belong_to_plan(self) -> None:
        plan = self.seed_plan()
        create_student({"student_id": "2024-0003", "name": "Outside Student"})

        with self.assertRaises(ValueError):
            create_transaction(
                {
                    "plan_id": plan["plan_id"],
                    "student_id": "2024-0003",
                    "amount": 100,
                    "transaction_type": "PAYMENT",
                }
            )

    def test_approved_transaction_requires_eligible_approver(self) -> None:
        plan = self.seed_plan()
        with self.assertRaises(ValueError):
            create_transaction(
                {
                    "plan_id": plan["plan_id"],
                    "student_id": "2024-0002",
                    "amount": 100,
                    "transaction_type": "PAYMENT",
                    "approval_status": "Approved",
                }
            )

        transaction = create_transaction(
            {
                "plan_id": plan["plan_id"],
                "student_id": "2024-0002",
                "approver_id": "2024-0001",
                "amount": 100,
                "transaction_type": "PAYMENT",
                "approval_status": "Approved",
            }
        )
        self.assertEqual(transaction["approver_id"], "2024-0001")

    def test_expense_item_must_belong_to_selected_plan(self) -> None:
        first_plan = self.seed_plan()
        second_plan = create_budget_plan(
            {
                "academic_year": "2026-2027",
                "semester": "1st",
                "total_planned_budget": 500,
                "member_count": 1,
                "student_ids": ["2024-0001"],
            }
        )
        other_item = self.seed_item(second_plan["plan_id"])

        with self.assertRaises(ValueError):
            create_transaction(
                {
                    "plan_id": first_plan["plan_id"],
                    "budget_item_id": other_item["budget_item_id"],
                    "amount": 50,
                    "transaction_type": "EXPENSE",
                }
            )

    def test_delete_guards_for_linked_records(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        expense = create_transaction(
            {
                "plan_id": plan["plan_id"],
                "budget_item_id": item["budget_item_id"],
                "amount": 50,
                "transaction_type": "EXPENSE",
            }
        )

        with self.assertRaises(ValueError):
            delete_student("2024-0001")
        with self.assertRaises(ValueError):
            delete_budget_item(item["budget_item_id"])

        create_inventory_item(
            {
                "transaction_id": expense["transaction_id"],
                "item_name": "Printer",
                "quantity": 1,
                "item_condition": "New",
            }
        )
        self.assertTrue(delete_transaction(expense["transaction_id"]))
        self.assertEqual(list_inventory_items(), [])

    def test_decisioned_records_are_not_hard_deleted(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        approved_expense = create_transaction(
            {
                "plan_id": plan["plan_id"],
                "budget_item_id": item["budget_item_id"],
                "approver_id": "2024-0001",
                "amount": 75,
                "transaction_type": "EXPENSE",
                "approval_status": "Approved",
                "transaction_date": datetime.now().replace(microsecond=0).isoformat(),
            }
        )
        inventory = create_inventory_item(
            {
                "transaction_id": approved_expense["transaction_id"],
                "item_name": "Projector",
                "quantity": 1,
                "item_condition": "Good",
            }
        )

        with self.assertRaises(ValueError):
            delete_transaction(approved_expense["transaction_id"])
        with self.assertRaises(ValueError):
            delete_inventory_item(inventory["inventory_item_id"])


if __name__ == "__main__":
    unittest.main()
