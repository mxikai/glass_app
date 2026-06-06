from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from services.budget_service import (
    create_budget_item,
    create_budget_plan,
    create_fund_bucket,
    delete_budget_item,
    update_budget_item,
    update_budget_plan,
    update_fund_bucket,
)
from services.dashboard_service import get_dashboard_summary
from services.inventory_service import (
    create_inventory_item,
    delete_inventory_item,
    list_inventory_items,
)
from services.report_service import generate_report_pdf, get_report_data
from services.student_service import create_student, delete_student
from services.transaction_service import create_transaction, delete_transaction, list_transactions, update_transaction
from utils import db
from utils.validators import academic_year_value, iso_date_value, student_id_value


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

    def expense_payload(self, plan_id: int, item_id: int, amount: float = 50, **extra) -> dict:
        return {
            "plan_id": plan_id,
            "budget_item_id": item_id,
            "amount": amount,
            "transaction_type": "EXPENSE",
            "line_items": [
                {
                    "item_name": "Supplies",
                    "quantity": 1,
                    "unit_cost": amount,
                }
            ],
            **extra,
        }


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
                "total_planned_budget": 1000,
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

    def test_budget_caps_limit_child_allocations(self) -> None:
        plan = self.seed_plan()
        create_fund_bucket(
            {
                "plan_id": plan["plan_id"],
                "bucket_name": "Events",
                "planned_amount": 900,
            }
        )

        with self.assertRaises(ValueError):
            create_fund_bucket(
                {
                    "plan_id": plan["plan_id"],
                    "bucket_name": "Supplies",
                    "planned_amount": 101,
                }
            )

        bucket = create_fund_bucket(
            {
                "plan_id": plan["plan_id"],
                "bucket_name": "Training",
                "planned_amount": 100,
            }
        )
        create_budget_item(
            {
                "bucket_id": bucket["bucket_id"],
                "item_name": "Materials",
                "planned_amount": 80,
            }
        )
        with self.assertRaises(ValueError):
            create_budget_item(
                {
                    "bucket_id": bucket["bucket_id"],
                    "item_name": "Snacks",
                    "planned_amount": 21,
                }
            )

    def test_lowering_caps_below_existing_children_is_rejected(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])

        with self.assertRaises(ValueError):
            update_budget_plan(plan["plan_id"], {"total_planned_budget": 500})

        with self.assertRaises(ValueError):
            update_fund_bucket(item["bucket_id"], {"planned_amount": 299})

    def test_budget_item_cap_counts_pending_and_approved_expenses(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        create_transaction(self.expense_payload(plan["plan_id"], item["budget_item_id"], 250))

        with self.assertRaises(ValueError):
            create_transaction(self.expense_payload(plan["plan_id"], item["budget_item_id"], 51))

    def test_rejected_and_void_expenses_do_not_reserve_budget(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        create_transaction(
            self.expense_payload(
                plan["plan_id"],
                item["budget_item_id"],
                300,
                approval_status="Rejected",
            )
        )
        create_transaction(
            self.expense_payload(
                plan["plan_id"],
                item["budget_item_id"],
                300,
                transaction_status="Void",
                notes="Cancelled request",
            )
        )

        expense = create_transaction(
            self.expense_payload(plan["plan_id"], item["budget_item_id"], 300)
        )
        self.assertEqual(expense["amount"], 300.0)

    def test_expense_update_excludes_itself_from_cap_total(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        expense = create_transaction(self.expense_payload(plan["plan_id"], item["budget_item_id"], 250))

        updated = update_transaction(
            expense["transaction_id"],
            {"line_items": [{"item_name": "Supplies", "quantity": 1, "unit_cost": 300}]},
        )
        self.assertEqual(updated["amount"], 300.0)

        with self.assertRaises(ValueError):
            update_transaction(
                expense["transaction_id"],
                {"line_items": [{"item_name": "Supplies", "quantity": 1, "unit_cost": 301}]},
            )

    def test_budget_item_lowering_and_override_obey_reserved_cap(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        create_transaction(self.expense_payload(plan["plan_id"], item["budget_item_id"], 120))

        with self.assertRaises(ValueError):
            update_budget_item(item["budget_item_id"], {"planned_amount": 119})

        with self.assertRaises(ValueError):
            create_transaction(
                {
                    "plan_id": plan["plan_id"],
                    "budget_item_id": item["budget_item_id"],
                    "transaction_type": "EXPENSE",
                    "amount": 181,
                    "amount_override_reason": "Receipt total",
                    "line_items": [{"item_name": "Supplies", "quantity": 1, "unit_cost": 150}],
                }
            )

    def test_delete_guards_for_linked_records(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        expense = create_transaction(
            self.expense_payload(plan["plan_id"], item["budget_item_id"], 50)
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
            self.expense_payload(
                plan["plan_id"],
                item["budget_item_id"],
                75,
                approver_id="2024-0001",
                approval_status="Approved",
                transaction_date=datetime.now().replace(microsecond=0).isoformat(),
            )
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

    def test_expense_line_items_compute_amount_and_require_override_reason(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])

        transaction = create_transaction(
            {
                "plan_id": plan["plan_id"],
                "budget_item_id": item["budget_item_id"],
                "transaction_type": "EXPENSE",
                "line_items": [
                    {"item_name": "Stapler", "quantity": 3, "unit_cost": 25},
                    {"item_name": "Tape", "quantity": 2, "unit_cost": 10},
                ],
            }
        )

        self.assertEqual(transaction["amount"], 95.0)
        self.assertEqual(transaction["computed_line_total"], 95.0)
        self.assertEqual(transaction["amount_delta"], 0.0)
        self.assertEqual(len(transaction["line_items"]), 2)

        with self.assertRaises(ValueError):
            create_transaction(
                {
                    "plan_id": plan["plan_id"],
                    "budget_item_id": item["budget_item_id"],
                    "transaction_type": "EXPENSE",
                    "amount": 90,
                    "line_items": [{"item_name": "Stapler", "quantity": 3, "unit_cost": 25}],
                }
            )

        discounted = create_transaction(
            {
                "plan_id": plan["plan_id"],
                "budget_item_id": item["budget_item_id"],
                "transaction_type": "EXPENSE",
                "amount": 70,
                "amount_override_reason": "Supplier discount",
                "line_items": [{"item_name": "Stapler", "quantity": 3, "unit_cost": 25}],
            }
        )
        self.assertEqual(discounted["amount_delta"], -5.0)
        self.assertEqual(discounted["amount_override_reason"], "Supplier discount")

        updated = update_transaction(
            transaction["transaction_id"],
            {"line_items": [{"item_name": "Stapler", "quantity": 1, "unit_cost": 30}]},
        )
        self.assertEqual(updated["amount"], 30.0)
        self.assertEqual(updated["computed_line_total"], 30.0)

    def test_payment_rejects_line_items(self) -> None:
        plan = self.seed_plan()
        with self.assertRaises(ValueError):
            create_transaction(
                {
                    "plan_id": plan["plan_id"],
                    "student_id": "2024-0002",
                    "amount": 100,
                    "transaction_type": "PAYMENT",
                    "line_items": [{"item_name": "Invalid", "quantity": 1, "unit_cost": 100}],
                }
            )

    def test_inventory_supports_purchase_line_link_and_legacy_source(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        expense = create_transaction(
            {
                "plan_id": plan["plan_id"],
                "budget_item_id": item["budget_item_id"],
                "transaction_type": "EXPENSE",
                "line_items": [{"item_name": "Stapler", "quantity": 3, "unit_cost": 25}],
            }
        )
        line_item = expense["line_items"][0]

        purchased = create_inventory_item(
            {
                "source_type": "Purchase",
                "transaction_id": expense["transaction_id"],
                "expense_line_item_id": line_item["line_item_id"],
                "item_name": "Stapler",
                "quantity": 3,
                "unit_cost": 25,
                "item_condition": "New",
            }
        )
        self.assertEqual(purchased["expense_line_item_id"], line_item["line_item_id"])
        self.assertEqual(purchased["unit_cost"], 25.0)

        with self.assertRaises(ValueError):
            create_inventory_item(
                {
                    "source_type": "Legacy",
                    "item_name": "Old Cabinet",
                    "quantity": 1,
                    "item_condition": "Good",
                }
            )

        legacy = create_inventory_item(
            {
                "source_type": "Legacy",
                "item_name": "Old Cabinet",
                "quantity": 1,
                "unit_cost": 500,
                "item_condition": "Good",
                "source_note": "Turned over by previous admin",
            }
        )
        self.assertIsNone(legacy["transaction_id"])
        self.assertEqual(legacy["source_type"], "Legacy")

    def test_dashboard_totals_use_only_approved_active_transactions(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        create_transaction(
            {
                "plan_id": plan["plan_id"],
                "student_id": "2024-0002",
                "amount": 100,
                "transaction_type": "PAYMENT",
            }
        )
        create_transaction(
            {
                "plan_id": plan["plan_id"],
                "student_id": "2024-0001",
                "approver_id": "2024-0001",
                "amount": 100,
                "transaction_type": "PAYMENT",
                "approval_status": "Approved",
            }
        )
        create_transaction(self.expense_payload(plan["plan_id"], item["budget_item_id"], 40))
        create_transaction(
            self.expense_payload(
                plan["plan_id"],
                item["budget_item_id"],
                25,
                approver_id="2024-0001",
                approval_status="Approved",
            )
        )

        summary = get_dashboard_summary(plan["plan_id"])
        self.assertEqual(summary["totals"]["payments"], 100.0)
        self.assertEqual(summary["totals"]["expenses"], 25.0)
        self.assertEqual(summary["totals"]["available_funds"], 75.0)
        self.assertEqual(summary["collection_progress"]["paid_count"], 1)
        self.assertEqual(summary["collection_progress"]["pending_count"], 1)

    def test_dashboard_and_reports_default_to_active_plan(self) -> None:
        active_plan = self.seed_plan()
        create_budget_plan(
            {
                "academic_year": "2026-2027",
                "semester": "1st",
                "total_planned_budget": 500,
                "member_count": 1,
                "student_ids": ["2024-0001"],
                "status": "Archived",
            }
        )

        summary = get_dashboard_summary()
        report = get_report_data("budget-plan")

        self.assertEqual(summary["active_plan"]["plan_id"], active_plan["plan_id"])
        self.assertEqual(report["plan"]["plan_id"], active_plan["plan_id"])

    def test_transaction_hash_chain_rebuilds_after_update(self) -> None:
        plan = self.seed_plan()
        first = create_transaction(
            {
                "plan_id": plan["plan_id"],
                "student_id": "2024-0001",
                "amount": 100,
                "transaction_type": "PAYMENT",
            }
        )
        second = create_transaction(
            {
                "plan_id": plan["plan_id"],
                "student_id": "2024-0002",
                "amount": 100,
                "transaction_type": "PAYMENT",
            }
        )
        self.assertEqual(len(first["current_hash"]), 64)
        self.assertEqual(second["previous_hash"], first["current_hash"])

        update_transaction(first["transaction_id"], {"notes": "Edited"})
        rows = list_transactions()
        updated_first = rows[0]
        updated_second = rows[1]
        self.assertNotEqual(updated_first["current_hash"], first["current_hash"])
        self.assertEqual(updated_second["previous_hash"], updated_first["current_hash"])

    def test_reports_json_and_pdf_are_generated(self) -> None:
        plan = self.seed_plan()
        item = self.seed_item(plan["plan_id"])
        create_transaction(
            self.expense_payload(
                plan["plan_id"],
                item["budget_item_id"],
                25,
                approver_id="2024-0001",
                approval_status="Approved",
            )
        )

        report = get_report_data("expense", plan["plan_id"])
        self.assertEqual(report["report_type"], "expense")
        self.assertEqual(len(report["expenses"]), 1)
        pdf = generate_report_pdf("expense", plan["plan_id"])
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 500)

    def test_existing_schema_migration_backfills_expense_line_items(self) -> None:
        original_path = db.DATABASE_PATH
        original_url = db.DB_URL
        original_engine = db._engine
        original_session = db._SessionLocal
        if db._engine is not None:
            db._engine.dispose()

        old_path = Path(self.tmp.name) / "old-glass.db"
        connection = sqlite3.connect(old_path)
        connection.executescript(
            """
            CREATE TABLE students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE budget_plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                academic_year TEXT NOT NULL,
                semester TEXT NOT NULL,
                total_planned_budget REAL NOT NULL,
                member_count INTEGER NOT NULL,
                semestral_fee_amount REAL NOT NULL
            );
            CREATE TABLE fund_buckets (
                bucket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                bucket_name TEXT NOT NULL,
                planned_amount REAL NOT NULL
            );
            CREATE TABLE budget_items (
                budget_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bucket_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                planned_amount REAL NOT NULL
            );
            CREATE TABLE transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                budget_item_id INTEGER,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL
            );
            CREATE TABLE inventory_items (
                inventory_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity INTEGER,
                item_condition TEXT,
                status TEXT,
                date_recorded TEXT
            );
            INSERT INTO budget_plans VALUES (1, '2025-2026', '1st', 1000, 1, 1000);
            INSERT INTO fund_buckets VALUES (1, 1, 'Operations', 500);
            INSERT INTO budget_items VALUES (1, 1, 'Supplies', 300);
            INSERT INTO transactions VALUES (1, 1, 1, 75, 'EXPENSE');
            INSERT INTO inventory_items VALUES (1, 1, 'Stapler', 3, 'Good', 'Active', '2026-06-01');
            """
        )
        connection.commit()
        connection.close()

        try:
            db.DATABASE_PATH = old_path
            db.DB_URL = f"sqlite:///{old_path}"
            db._engine = None
            db._SessionLocal = None
            db.init_db()
            connection = sqlite3.connect(old_path)
            line_item = connection.execute(
                "SELECT item_name, quantity, unit_cost FROM expense_line_items WHERE transaction_id = 1"
            ).fetchone()
            inventory_columns = {
                row[1]: row[3]
                for row in connection.execute("PRAGMA table_info(inventory_items)").fetchall()
            }
            inventory = connection.execute(
                "SELECT source_type, transaction_id FROM inventory_items WHERE inventory_item_id = 1"
            ).fetchone()
            connection.close()
        finally:
            if db._engine is not None:
                db._engine.dispose()
            db.DATABASE_PATH = original_path
            db.DB_URL = original_url
            db._engine = original_engine
            db._SessionLocal = original_session

        self.assertEqual(line_item, ("Supplies", 1, 75))
        self.assertIn("source_type", inventory_columns)
        self.assertFalse(bool(inventory_columns["transaction_id"]))
        self.assertEqual(inventory, ("Purchase", 1))


if __name__ == "__main__":
    unittest.main()
