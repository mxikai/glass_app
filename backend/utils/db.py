from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import shutil

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_PATH, DB_URL

Base = declarative_base()

_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=_get_engine(), autoflush=False, autocommit=False)
    return _SessionLocal


@contextmanager
def session_scope():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _table_exists(connection, table_name: str) -> bool:
    row = connection.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _columns(connection, table_name: str) -> dict[str, dict]:
    rows = connection.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
    return {
        row[1]: {
            "type": row[2],
            "notnull": bool(row[3]),
            "default": row[4],
            "pk": bool(row[5]),
        }
        for row in rows
    }


def _source(columns: dict[str, dict], column_name: str, fallback: str) -> str:
    return column_name if column_name in columns else fallback


def _first_source(columns: dict[str, dict], column_names: list[str], fallback: str) -> str:
    for column_name in column_names:
        if column_name in columns:
            return column_name
    return fallback


def _add_column_if_missing(connection, table_name: str, column_name: str, column_sql: str) -> None:
    if column_name not in _columns(connection, table_name):
        connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def _backup_database_for_migration() -> None:
    db_path = Path(DATABASE_PATH)
    if not db_path.exists() or db_path.name == ":memory:":
        return

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = db_path.with_name(f"{db_path.name}.bak-{timestamp}")
    counter = 1
    while backup_path.exists():
        backup_path = db_path.with_name(f"{db_path.name}.bak-{timestamp}-{counter}")
        counter += 1
    shutil.copy2(db_path, backup_path)


def _rebuild_base_inventory_item(connection) -> None:
    columns = _columns(connection, "InventoryItem")

    def source(column_name: str, fallback: str) -> str:
        return _source(columns, column_name, fallback)

    connection.exec_driver_sql("PRAGMA foreign_keys = OFF")
    connection.exec_driver_sql("ALTER TABLE InventoryItem RENAME TO InventoryItem_old")
    connection.exec_driver_sql(
        """
        CREATE TABLE InventoryItem (
            InventoryItemID INTEGER PRIMARY KEY AUTOINCREMENT,
            PurchaseTransactionID INTEGER,
            ExpenseLineItemID INTEGER,
            ItemName VARCHAR(120) NOT NULL,
            Quantity INTEGER,
            UnitCost NUMERIC(12, 2),
            ItemCondition VARCHAR(50),
            SourceType VARCHAR(20),
            SourceNote TEXT,
            Status VARCHAR(20),
            DateRecorded DATE,
            FOREIGN KEY(PurchaseTransactionID) REFERENCES TransactionRecord (TransactionID),
            FOREIGN KEY(ExpenseLineItemID) REFERENCES ExpenseLineItem (LineItemID)
        )
        """
    )
    connection.exec_driver_sql(
        f"""
        INSERT INTO InventoryItem (
            InventoryItemID,
            PurchaseTransactionID,
            ExpenseLineItemID,
            ItemName,
            Quantity,
            UnitCost,
            ItemCondition,
            SourceType,
            SourceNote,
            Status,
            DateRecorded
        )
        SELECT
            InventoryItemID,
            PurchaseTransactionID,
            {source("ExpenseLineItemID", "NULL")},
            ItemName,
            Quantity,
            {source("UnitCost", "NULL")},
            ItemCondition,
            COALESCE({source("SourceType", "NULL")}, 'Purchase'),
            {source("SourceNote", "NULL")},
            Status,
            DateRecorded
        FROM InventoryItem_old
        """
    )
    connection.exec_driver_sql("DROP TABLE InventoryItem_old")
    connection.exec_driver_sql("PRAGMA foreign_keys = ON")


def _copy_lowercase_schema_to_base(connection) -> None:
    old_tables = [
        "students",
        "budget_plans",
        "budget_plan_students",
        "fund_buckets",
        "budget_items",
        "transactions",
        "expense_line_items",
        "inventory_items",
    ]
    if not any(_table_exists(connection, table_name) for table_name in old_tables):
        return

    _backup_database_for_migration()

    if _table_exists(connection, "students"):
        columns = _columns(connection, "students")
        connection.exec_driver_sql(
            f"""
            INSERT OR IGNORE INTO Student (
                StudentID,
                Name,
                Program,
                YearLevel,
                RoleTitle,
                CanApprove,
                Status
            )
            SELECT
                student_id,
                name,
                {_source(columns, "program", "NULL")},
                {_source(columns, "year_level", "NULL")},
                {_source(columns, "role_title", "NULL")},
                COALESCE({_source(columns, "can_approve", "0")}, 0),
                COALESCE({_source(columns, "status", "'Active'")}, 'Active')
            FROM students
            """
        )

    if _table_exists(connection, "budget_plans"):
        columns = _columns(connection, "budget_plans")
        connection.exec_driver_sql(
            f"""
            INSERT OR IGNORE INTO BudgetPlan (
                PlanID,
                AcademicYear,
                Semester,
                TotalPlannedBudget,
                MemberCount,
                SemestralFeeAmount,
                ApprovalStatus,
                ApprovedDate,
                Status
            )
            SELECT
                plan_id,
                academic_year,
                semester,
                total_planned_budget,
                member_count,
                COALESCE(
                    {_source(columns, "semestral_fee_amount", "NULL")},
                    total_planned_budget / NULLIF(member_count, 0),
                    0
                ),
                COALESCE({_source(columns, "approval_status", "'Pending'")}, 'Pending'),
                {_source(columns, "approved_date", "NULL")},
                COALESCE({_source(columns, "status", "'Active'")}, 'Active')
            FROM budget_plans
            """
        )

    if _table_exists(connection, "budget_plan_students"):
        columns = _columns(connection, "budget_plan_students")
        connection.exec_driver_sql(
            f"""
            INSERT OR IGNORE INTO BudgetPlanStudent (
                PlanID,
                StudentID,
                DateIncluded,
                FeeStatus
            )
            SELECT
                plan_id,
                student_id,
                COALESCE({_source(columns, "date_included", "NULL")}, date('now')),
                COALESCE({_source(columns, "fee_status", "'Pending'")}, 'Pending')
            FROM budget_plan_students
            """
        )

    if _table_exists(connection, "fund_buckets"):
        columns = _columns(connection, "fund_buckets")
        connection.exec_driver_sql(
            f"""
            INSERT OR IGNORE INTO FundBucket (
                BucketID,
                PlanID,
                BucketName,
                PlannedAmount,
                Description
            )
            SELECT
                bucket_id,
                plan_id,
                bucket_name,
                planned_amount,
                {_source(columns, "description", "NULL")}
            FROM fund_buckets
            """
        )

    if _table_exists(connection, "budget_items"):
        columns = _columns(connection, "budget_items")
        connection.exec_driver_sql(
            f"""
            INSERT OR IGNORE INTO BudgetItem (
                BudgetItemID,
                BucketID,
                ItemName,
                ItemType,
                PlannedAmount,
                Description
            )
            SELECT
                budget_item_id,
                bucket_id,
                item_name,
                {_source(columns, "item_type", "NULL")},
                planned_amount,
                {_source(columns, "description", "NULL")}
            FROM budget_items
            """
        )

    if _table_exists(connection, "transactions"):
        columns = _columns(connection, "transactions")
        connection.exec_driver_sql(
            f"""
            INSERT OR IGNORE INTO TransactionRecord (
                TransactionID,
                PlanID,
                StudentID,
                BudgetItemID,
                ApprovedByStudentID,
                Amount,
                TransactionType,
                TransactionStatus,
                ApprovalStatus,
                TransactionDate,
                Notes,
                ReceiptPath,
                AmountOverrideReason,
                CurrentHash,
                PreviousHash
            )
            SELECT
                transaction_id,
                plan_id,
                {_source(columns, "student_id", "NULL")},
                {_source(columns, "budget_item_id", "NULL")},
                {_first_source(columns, ["approver_id", "approved_by_student_id"], "NULL")},
                amount,
                transaction_type,
                COALESCE({_source(columns, "transaction_status", "'Active'")}, 'Active'),
                COALESCE({_source(columns, "approval_status", "'Pending'")}, 'Pending'),
                {_source(columns, "transaction_date", "NULL")},
                {_source(columns, "notes", "NULL")},
                {_source(columns, "receipt_path", "NULL")},
                {_source(columns, "amount_override_reason", "NULL")},
                {_source(columns, "current_hash", "NULL")},
                {_source(columns, "previous_hash", "NULL")}
            FROM transactions
            """
        )

    if _table_exists(connection, "expense_line_items"):
        columns = _columns(connection, "expense_line_items")
        connection.exec_driver_sql(
            f"""
            INSERT OR IGNORE INTO ExpenseLineItem (
                LineItemID,
                TransactionID,
                ItemName,
                Quantity,
                UnitCost
            )
            SELECT
                line_item_id,
                transaction_id,
                item_name,
                COALESCE({_source(columns, "quantity", "1")}, 1),
                unit_cost
            FROM expense_line_items
            """
        )

    if _table_exists(connection, "inventory_items"):
        columns = _columns(connection, "inventory_items")
        connection.exec_driver_sql(
            f"""
            INSERT OR IGNORE INTO InventoryItem (
                InventoryItemID,
                PurchaseTransactionID,
                ExpenseLineItemID,
                ItemName,
                Quantity,
                UnitCost,
                ItemCondition,
                SourceType,
                SourceNote,
                Status,
                DateRecorded
            )
            SELECT
                inventory_item_id,
                {_source(columns, "transaction_id", "NULL")},
                {_source(columns, "expense_line_item_id", "NULL")},
                item_name,
                COALESCE({_source(columns, "quantity", "1")}, 1),
                {_source(columns, "unit_cost", "NULL")},
                {_source(columns, "item_condition", "NULL")},
                COALESCE({_source(columns, "source_type", "NULL")}, 'Purchase'),
                {_source(columns, "source_note", "NULL")},
                COALESCE({_source(columns, "status", "'Active'")}, 'Active'),
                {_source(columns, "date_recorded", "NULL")}
            FROM inventory_items
            """
        )

    _backfill_expense_line_items(connection)

    connection.exec_driver_sql("PRAGMA foreign_keys = OFF")
    for table_name in reversed(old_tables):
        connection.exec_driver_sql(f"DROP TABLE IF EXISTS {table_name}")
    connection.exec_driver_sql("PRAGMA foreign_keys = ON")


def _backfill_expense_line_items(connection) -> None:
    if not _table_exists(connection, "ExpenseLineItem") or not _table_exists(connection, "TransactionRecord"):
        return
    connection.exec_driver_sql(
        """
        INSERT INTO ExpenseLineItem (TransactionID, ItemName, Quantity, UnitCost)
        SELECT
            TransactionRecord.TransactionID,
            COALESCE(BudgetItem.ItemName, 'Expense'),
            1,
            TransactionRecord.Amount
        FROM TransactionRecord
        LEFT JOIN BudgetItem
            ON BudgetItem.BudgetItemID = TransactionRecord.BudgetItemID
        WHERE TransactionRecord.TransactionType = 'EXPENSE'
            AND NOT EXISTS (
                SELECT 1
                FROM ExpenseLineItem
                WHERE ExpenseLineItem.TransactionID = TransactionRecord.TransactionID
            )
        """
    )


def _ensure_base_schema_extensions(connection) -> None:
    if _table_exists(connection, "BudgetPlanStudent"):
        _add_column_if_missing(connection, "BudgetPlanStudent", "DateIncluded", "DateIncluded DATE")
        _add_column_if_missing(
            connection,
            "BudgetPlanStudent",
            "FeeStatus",
            "FeeStatus VARCHAR(10) DEFAULT 'Pending'",
        )
        connection.exec_driver_sql(
            "UPDATE BudgetPlanStudent SET DateIncluded = date('now') WHERE DateIncluded IS NULL"
        )
        connection.exec_driver_sql(
            "UPDATE BudgetPlanStudent SET FeeStatus = 'Pending' WHERE FeeStatus IS NULL"
        )

    if _table_exists(connection, "TransactionRecord"):
        _add_column_if_missing(
            connection,
            "TransactionRecord",
            "AmountOverrideReason",
            "AmountOverrideReason TEXT",
        )

    if _table_exists(connection, "InventoryItem"):
        inventory_columns = _columns(connection, "InventoryItem")
        needs_rebuild = (
            "SourceType" not in inventory_columns
            or "SourceNote" not in inventory_columns
            or "UnitCost" not in inventory_columns
            or "ExpenseLineItemID" not in inventory_columns
            or inventory_columns.get("PurchaseTransactionID", {}).get("notnull", False)
        )
        if needs_rebuild:
            _rebuild_base_inventory_item(connection)

    _backfill_expense_line_items(connection)


def _migrate_existing_schema() -> None:
    engine = _get_engine()
    with engine.begin() as connection:
        _copy_lowercase_schema_to_base(connection)
        _ensure_base_schema_extensions(connection)


def init_db():
    # Import models to register them with SQLAlchemy before creating tables.
    import models  # noqa: F401

    Base.metadata.create_all(bind=_get_engine())
    _migrate_existing_schema()
