from __future__ import annotations

from models.expense_line_item_model import ExpenseLineItem
from models.inventory_model import InventoryItem
from models.transaction_model import Transaction
from utils.db import session_scope
from utils.validators import (
    INVENTORY_CONDITIONS,
    INVENTORY_SOURCE_TYPES,
    INVENTORY_STATUSES,
    choice_value,
    decimal_value,
    int_value,
    iso_date_value,
    text_value,
)


def _inventory_payload(data: dict, *, current: dict | None = None) -> dict:
    source = {**(current or {}), **data}
    source_type = choice_value(
        source.get("source_type"),
        "source_type",
        INVENTORY_SOURCE_TYPES,
        default="Purchase",
    )
    transaction_id = int_value(
        source.get("transaction_id"),
        "transaction_id",
        required=source_type == "Purchase",
        min_value=1,
    )
    expense_line_item_id = int_value(
        source.get("expense_line_item_id"),
        "expense_line_item_id",
        required=False,
        min_value=1,
    )
    source_note = text_value(source.get("source_note"), "source_note", max_length=500)
    if source_type == "Legacy":
        if not source_note:
            raise ValueError("source_note is required for Legacy inventory")
        transaction_id = None
        expense_line_item_id = None

    return {
        "source_type": source_type,
        "transaction_id": transaction_id,
        "expense_line_item_id": expense_line_item_id,
        "item_name": text_value(source.get("item_name"), "item_name", required=True, max_length=120),
        "quantity": int_value(source.get("quantity", 1), "quantity", min_value=1, max_value=999_999),
        "unit_cost": decimal_value(source.get("unit_cost"), "unit_cost", required=False),
        "item_condition": choice_value(
            source.get("item_condition"),
            "item_condition",
            INVENTORY_CONDITIONS,
            required=False,
        ),
        "source_note": source_note,
        "status": choice_value(
            source.get("status"),
            "status",
            INVENTORY_STATUSES,
            default="Active",
        ),
        "date_recorded": iso_date_value(
            source.get("date_recorded"),
            "date_recorded",
            no_future=True,
        ),
    }


def _require_purchase_source(
    session,
    transaction_id: int | None,
    expense_line_item_id: int | None,
) -> tuple[Transaction, ExpenseLineItem | None]:
    if transaction_id is None:
        raise ValueError("transaction_id is required for Purchase inventory")
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise ValueError("Invalid transaction_id")
    if transaction.transaction_type != "EXPENSE":
        raise ValueError("Inventory items must reference an EXPENSE transaction")

    line_item = None
    if expense_line_item_id is not None:
        line_item = session.get(ExpenseLineItem, expense_line_item_id)
        if not line_item:
            raise ValueError("Invalid expense_line_item_id")
        if line_item.transaction_id != transaction_id:
            raise ValueError("expense_line_item_id must belong to the selected transaction")
    return transaction, line_item


# Inventory

def list_inventory_items() -> list[dict]:
    with session_scope() as session:
        items = session.query(InventoryItem).order_by(InventoryItem.inventory_item_id).all()
        return [item.to_dict() for item in items]


def get_inventory_item(item_id: int) -> dict | None:
    with session_scope() as session:
        item = session.get(InventoryItem, item_id)
        return item.to_dict() if item else None


def create_inventory_item(data: dict) -> dict:
    payload = _inventory_payload(data)

    with session_scope() as session:
        if payload["source_type"] == "Purchase":
            _require_purchase_source(
                session,
                payload["transaction_id"],
                payload["expense_line_item_id"],
            )

        item = InventoryItem(
            source_type=payload["source_type"],
            transaction_id=payload["transaction_id"],
            expense_line_item_id=payload["expense_line_item_id"],
            item_name=payload["item_name"],
            quantity=payload["quantity"],
            unit_cost=payload["unit_cost"],
            item_condition=payload["item_condition"],
            source_note=payload["source_note"],
            status=payload["status"],
            date_recorded=payload["date_recorded"],
        )
        session.add(item)
        session.flush()
        return item.to_dict()


def update_inventory_item(item_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        item = session.get(InventoryItem, item_id)
        if not item:
            return None

        payload = _inventory_payload(data, current=item.to_dict())
        if payload["source_type"] == "Purchase":
            _require_purchase_source(
                session,
                payload["transaction_id"],
                payload["expense_line_item_id"],
            )

        for field in [
            "source_type",
            "transaction_id",
            "expense_line_item_id",
            "item_name",
            "quantity",
            "unit_cost",
            "item_condition",
            "source_note",
            "status",
        ]:
            setattr(item, field, payload[field])
        item.date_recorded = payload["date_recorded"]

        session.flush()
        return item.to_dict()


def delete_inventory_item(item_id: int) -> bool:
    with session_scope() as session:
        item = session.get(InventoryItem, item_id)
        if not item:
            return False
        if item.transaction and item.transaction.approval_status != "Pending":
            raise ValueError(
                f"Cannot delete inventory item #{item_id} because its expense is "
                f"{item.transaction.approval_status}. Set status to Archived instead."
            )
        session.delete(item)
        return True
