from __future__ import annotations

from datetime import date

from models.inventory_model import InventoryItem
from models.transaction_model import Transaction
from utils.db import session_scope
from utils.validators import require_fields


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


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
    require_fields(data, ["transaction_id", "item_name"])

    with session_scope() as session:
        transaction = session.get(Transaction, data["transaction_id"])
        if not transaction:
            raise ValueError("Invalid transaction_id")

        item = InventoryItem(
            transaction_id=data["transaction_id"],
            item_name=data["item_name"],
            quantity=data.get("quantity", 1),
            item_condition=data.get("item_condition"),
            status=data.get("status", "Active"),
            date_recorded=_parse_date(data.get("date_recorded")),
        )
        session.add(item)
        session.flush()
        return item.to_dict()


def update_inventory_item(item_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        item = session.get(InventoryItem, item_id)
        if not item:
            return None

        for field in ["item_name", "quantity", "item_condition", "status"]:
            if field in data:
                setattr(item, field, data[field])

        if "date_recorded" in data:
            item.date_recorded = _parse_date(data.get("date_recorded"))

        session.flush()
        return item.to_dict()


def delete_inventory_item(item_id: int) -> bool:
    with session_scope() as session:
        item = session.get(InventoryItem, item_id)
        if not item:
            return False
        session.delete(item)
        return True
