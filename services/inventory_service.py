from __future__ import annotations

from models.inventory_model import InventoryItem
from models.transaction_model import Transaction
from utils.db import session_scope
from utils.validators import (
    INVENTORY_CONDITIONS,
    INVENTORY_STATUSES,
    choice_value,
    int_value,
    iso_date_value,
    text_value,
)


def _inventory_payload(data: dict, *, current: dict | None = None) -> dict:
    source = {**(current or {}), **data}
    return {
        "transaction_id": int_value(source.get("transaction_id"), "transaction_id", min_value=1),
        "item_name": text_value(source.get("item_name"), "item_name", required=True, max_length=120),
        "quantity": int_value(source.get("quantity", 1), "quantity", min_value=1, max_value=999_999),
        "item_condition": choice_value(
            source.get("item_condition"),
            "item_condition",
            INVENTORY_CONDITIONS,
            required=False,
        ),
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


def _require_expense_transaction(session, transaction_id: int) -> Transaction:
    transaction = session.get(Transaction, transaction_id)
    if not transaction:
        raise ValueError("Invalid transaction_id")
    if transaction.transaction_type != "EXPENSE":
        raise ValueError("Inventory items must reference an EXPENSE transaction")
    return transaction


# Inventory

def list_inventory_items() -> list[dict]:
    with session_scope() as session:
        items = session.query(InventoryItem).all()
        return [item.to_dict() for item in items]


def get_inventory_item(item_id: int) -> dict | None:
    with session_scope() as session:
        item = session.get(InventoryItem, item_id)
        return item.to_dict() if item else None


def create_inventory_item(data: dict) -> dict:
    payload = _inventory_payload(data)

    with session_scope() as session:
        _require_expense_transaction(session, payload["transaction_id"])

        item = InventoryItem(
            transaction_id=payload["transaction_id"],
            item_name=payload["item_name"],
            quantity=payload["quantity"],
            item_condition=payload["item_condition"],
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
        _require_expense_transaction(session, payload["transaction_id"])
        for field in ["item_name", "quantity", "item_condition", "status"]:
            setattr(item, field, payload[field])
        item.transaction_id = payload["transaction_id"]
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
