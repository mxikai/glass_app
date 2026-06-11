from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

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


def _add_column_if_missing(connection, table_name: str, column_name: str, column_sql: str) -> None:
    if column_name not in _columns(connection, table_name):
        connection.exec_driver_sql(f"ALTER TABLE {table_name} ADD COLUMN {column_sql}")


def _rebuild_inventory_items(connection) -> None:
    columns = _columns(connection, "inventory_items")

    def source(column_name: str, fallback: str) -> str:
        return column_name if column_name in columns else fallback

    connection.exec_driver_sql("PRAGMA foreign_keys = OFF")
    connection.exec_driver_sql("ALTER TABLE inventory_items RENAME TO inventory_items_old")
    connection.exec_driver_sql(
        """
        CREATE TABLE inventory_items (
            inventory_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER,
            expense_line_item_id INTEGER,
            item_name VARCHAR(120) NOT NULL,
            quantity INTEGER,
            unit_cost NUMERIC(12, 2),
            item_condition VARCHAR(50),
            source_type VARCHAR(20),
            source_note TEXT,
            status VARCHAR(20),
            date_recorded DATE,
            FOREIGN KEY(transaction_id) REFERENCES transactions (transaction_id),
            FOREIGN KEY(expense_line_item_id) REFERENCES expense_line_items (line_item_id)
        )
        """
    )
    connection.exec_driver_sql(
        f"""
        INSERT INTO inventory_items (
            inventory_item_id,
            transaction_id,
            expense_line_item_id,
            item_name,
            quantity,
            unit_cost,
            item_condition,
            source_type,
            source_note,
            status,
            date_recorded
        )
        SELECT
            inventory_item_id,
            transaction_id,
            {source("expense_line_item_id", "NULL")},
            item_name,
            quantity,
            {source("unit_cost", "NULL")},
            item_condition,
            COALESCE({source("source_type", "NULL")}, 'Purchase'),
            {source("source_note", "NULL")},
            status,
            date_recorded
        FROM inventory_items_old
        """
    )
    connection.exec_driver_sql("DROP TABLE inventory_items_old")
    connection.exec_driver_sql("PRAGMA foreign_keys = ON")


def _migrate_existing_schema() -> None:
    engine = _get_engine()
    with engine.begin() as connection:
        if _table_exists(connection, "transactions"):
            _add_column_if_missing(
                connection,
                "transactions",
                "amount_override_reason",
                "amount_override_reason TEXT",
            )

        if _table_exists(connection, "inventory_items"):
            inventory_columns = _columns(connection, "inventory_items")
            needs_rebuild = (
                "source_type" not in inventory_columns
                or "source_note" not in inventory_columns
                or "unit_cost" not in inventory_columns
                or "expense_line_item_id" not in inventory_columns
                or inventory_columns.get("transaction_id", {}).get("notnull", False)
            )
            if needs_rebuild:
                _rebuild_inventory_items(connection)

        if _table_exists(connection, "expense_line_items") and _table_exists(connection, "transactions"):
            connection.exec_driver_sql(
                """
                INSERT INTO expense_line_items (transaction_id, item_name, quantity, unit_cost)
                SELECT
                    transactions.transaction_id,
                    COALESCE(budget_items.item_name, 'Expense'),
                    1,
                    transactions.amount
                FROM transactions
                LEFT JOIN budget_items
                    ON budget_items.budget_item_id = transactions.budget_item_id
                WHERE transactions.transaction_type = 'EXPENSE'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM expense_line_items
                        WHERE expense_line_items.transaction_id = transactions.transaction_id
                    )
                """
            )


def init_db():
    # Import models to register them with SQLAlchemy before creating tables.
    import models  # noqa: F401

    Base.metadata.create_all(bind=_get_engine())
    _migrate_existing_schema()
