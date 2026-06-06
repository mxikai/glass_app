from __future__ import annotations

import json
from decimal import Decimal

from models.budget_item_model import BudgetItem
from models.budget_plan_model import BudgetPlan
from models.expense_line_item_model import ExpenseLineItem
from models.student_model import Student
from models.transaction_model import Transaction
from services.budget_cap_service import ensure_expense_within_item_cap
from utils.db import session_scope
from utils.hash_utils import sha256
from utils.validators import (
    APPROVAL_STATUSES,
    TRANSACTION_STATUSES,
    TRANSACTION_TYPES,
    choice_value,
    decimal_value,
    int_value,
    iso_datetime_value,
    optional_student_id_value,
    student_id_value,
    text_value,
)


def _upper_transaction_type(value) -> str:
    text = text_value(value, "transaction_type", required=True, max_length=20)
    return choice_value((text or "").upper(), "transaction_type", TRANSACTION_TYPES) or ""


def _eligible_approver(session, approver_id: str | None, approval_status: str) -> str | None:
    approver_id = optional_student_id_value(approver_id, "approver_id")
    if not approver_id:
        if approval_status == "Approved":
            raise ValueError("approver_id is required for approved transactions")
        return None

    approver = session.get(Student, approver_id)
    if not approver or not approver.can_approve or approver.status != "Active":
        raise ValueError("approver_id must reference an active student with approval authority")
    return approver_id


def _line_items_value(value, *, required: bool) -> list[dict]:
    if value is None:
        if required:
            raise ValueError("line_items are required for EXPENSE transactions")
        return []
    if not isinstance(value, list):
        raise ValueError("line_items must be a list")
    if required and not value:
        raise ValueError("line_items are required for EXPENSE transactions")

    line_items = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"line_items[{index}] must be an object")
        quantity = int_value(
            item.get("quantity", 1),
            f"line_items[{index}].quantity",
            min_value=1,
            max_value=999_999,
        )
        unit_cost = decimal_value(item.get("unit_cost"), f"line_items[{index}].unit_cost")
        line_items.append(
            {
                "line_item_id": int_value(
                    item.get("line_item_id"),
                    f"line_items[{index}].line_item_id",
                    required=False,
                    min_value=1,
                ),
                "item_name": text_value(
                    item.get("item_name"),
                    f"line_items[{index}].item_name",
                    required=True,
                    max_length=120,
                ),
                "quantity": quantity,
                "unit_cost": unit_cost,
                "line_total": Decimal(str(quantity)) * (unit_cost or Decimal("0")),
            }
        )
    return line_items


def _computed_line_total(line_items: list[dict]) -> Decimal:
    return sum((item["line_total"] for item in line_items), Decimal("0"))


def _amount_value(data: dict, transaction_type: str, line_items: list[dict]) -> tuple[Decimal, str | None]:
    amount_input = data.get("amount")
    computed = _computed_line_total(line_items)
    if transaction_type == "EXPENSE" and amount_input is None:
        amount = computed
    else:
        amount = decimal_value(amount_input, "amount")

    reason = text_value(
        data.get("amount_override_reason"),
        "amount_override_reason",
        max_length=255,
    )
    if transaction_type == "EXPENSE" and amount != computed:
        if not reason:
            raise ValueError("amount_override_reason is required when amount differs from line item total")
        return amount, reason
    return amount, None


def _transaction_payload(data: dict, session) -> dict:
    plan_id = int_value(data.get("plan_id"), "plan_id", min_value=1)
    plan = session.get(BudgetPlan, plan_id)
    if not plan:
        raise ValueError("Invalid plan_id")

    transaction_type = _upper_transaction_type(data.get("transaction_type"))
    approval_status = choice_value(
        data.get("approval_status"),
        "approval_status",
        APPROVAL_STATUSES,
        default="Pending",
    )
    transaction_status = choice_value(
        data.get("transaction_status"),
        "transaction_status",
        TRANSACTION_STATUSES,
        default="Active",
    )
    notes = text_value(data.get("notes"), "notes", max_length=2000)
    if transaction_status == "Void" and not notes:
        raise ValueError("notes are required when setting a transaction to Void")

    student_id = optional_student_id_value(data.get("student_id"))
    budget_item_id = int_value(
        data.get("budget_item_id"),
        "budget_item_id",
        required=False,
        min_value=1,
    )

    if transaction_type == "PAYMENT":
        if data.get("line_items"):
            raise ValueError("PAYMENT transactions cannot include line_items")
        if data.get("amount_override_reason"):
            raise ValueError("PAYMENT transactions cannot include amount_override_reason")
        student_id = student_id_value(data.get("student_id"))
        if budget_item_id is not None:
            raise ValueError("PAYMENT transactions cannot include budget_item_id")
        student = session.get(Student, student_id)
        if not student:
            raise ValueError("Invalid student_id")
        plan_student_ids = {student.student_id for student in plan.students}
        if student_id not in plan_student_ids:
            raise ValueError("student_id must belong to the selected plan")
        line_items = []
    else:
        if student_id is not None:
            raise ValueError("EXPENSE transactions cannot include student_id")
        if budget_item_id is None:
            raise ValueError("budget_item_id is required for EXPENSE transactions")
        item = session.get(BudgetItem, budget_item_id)
        if not item:
            raise ValueError("Invalid budget_item_id")
        if not item.fund_bucket or item.fund_bucket.plan_id != plan_id:
            raise ValueError("budget_item_id must belong to the selected plan")
        line_items = _line_items_value(data.get("line_items"), required=True)

    amount, amount_override_reason = _amount_value(data, transaction_type, line_items)
    approver_id = _eligible_approver(session, data.get("approver_id"), approval_status or "Pending")
    return {
        "plan_id": plan_id,
        "student_id": student_id,
        "approver_id": approver_id,
        "budget_item_id": budget_item_id,
        "amount": amount,
        "amount_override_reason": amount_override_reason,
        "line_items": line_items,
        "transaction_type": transaction_type,
        "transaction_status": transaction_status,
        "approval_status": approval_status,
        "transaction_date": iso_datetime_value(
            data.get("transaction_date"),
            "transaction_date",
            no_future=True,
        ),
        "notes": notes,
        "receipt_path": text_value(data.get("receipt_path"), "receipt_path", max_length=255),
    }


def _replace_line_items(transaction: Transaction, line_items: list[dict]) -> None:
    existing_by_id = {
        line_item.line_item_id: line_item
        for line_item in transaction.expense_line_items
        if line_item.line_item_id is not None
    }
    next_line_items = []
    for item in line_items:
        line_item_id = item.get("line_item_id")
        line_item = existing_by_id.get(line_item_id) if line_item_id else None
        if line_item is None:
            line_item = ExpenseLineItem()
        line_item.item_name = item["item_name"]
        line_item.quantity = item["quantity"]
        line_item.unit_cost = item["unit_cost"]
        next_line_items.append(line_item)

    removed = [
        line_item
        for line_item in transaction.expense_line_items
        if line_item not in next_line_items
    ]
    if any(line_item.inventory_items for line_item in removed):
        raise ValueError("Cannot remove expense line items already linked to inventory")
    transaction.expense_line_items[:] = next_line_items


def _decimal_text(value) -> str:
    return str(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _transaction_hash_payload(transaction: Transaction, previous_hash: str | None) -> str:
    payload = {
        "transaction_id": transaction.transaction_id,
        "plan_id": transaction.plan_id,
        "student_id": transaction.student_id,
        "approver_id": transaction.approver_id,
        "budget_item_id": transaction.budget_item_id,
        "amount": _decimal_text(transaction.amount),
        "amount_override_reason": transaction.amount_override_reason,
        "transaction_type": transaction.transaction_type,
        "transaction_status": transaction.transaction_status,
        "approval_status": transaction.approval_status,
        "transaction_date": transaction.transaction_date.isoformat() if transaction.transaction_date else None,
        "notes": transaction.notes,
        "receipt_path": transaction.receipt_path,
        "line_items": [
            {
                "line_item_id": line_item.line_item_id,
                "item_name": line_item.item_name,
                "quantity": line_item.quantity,
                "unit_cost": _decimal_text(line_item.unit_cost),
            }
            for line_item in transaction.expense_line_items
        ],
        "previous_hash": previous_hash,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def rebuild_transaction_hash_chain(session) -> None:
    previous_hash = None
    transactions = session.query(Transaction).order_by(Transaction.transaction_id).all()
    for transaction in transactions:
        transaction.previous_hash = previous_hash
        transaction.current_hash = sha256(_transaction_hash_payload(transaction, previous_hash))
        previous_hash = transaction.current_hash


# Transactions

def list_transactions() -> list[dict]:
    with session_scope() as session:
        transactions = session.query(Transaction).order_by(Transaction.transaction_id).all()
        return [transaction.to_dict() for transaction in transactions]


def get_transaction(transaction_id: int) -> dict | None:
    with session_scope() as session:
        transaction = session.get(Transaction, transaction_id)
        return transaction.to_dict() if transaction else None


def create_transaction(data: dict) -> dict:
    with session_scope() as session:
        payload = _transaction_payload(data, session)
        if payload["transaction_type"] == "EXPENSE":
            ensure_expense_within_item_cap(
                session,
                payload["budget_item_id"],
                payload["amount"],
                transaction_status=payload["transaction_status"],
                approval_status=payload["approval_status"],
            )
        transaction = Transaction(
            plan_id=payload["plan_id"],
            student_id=payload["student_id"],
            approver_id=payload["approver_id"],
            budget_item_id=payload["budget_item_id"],
            amount=payload["amount"],
            amount_override_reason=payload["amount_override_reason"],
            transaction_type=payload["transaction_type"],
            transaction_status=payload["transaction_status"],
            approval_status=payload["approval_status"],
            transaction_date=payload["transaction_date"],
            notes=payload["notes"],
            receipt_path=payload["receipt_path"],
        )
        _replace_line_items(transaction, payload["line_items"])

        session.add(transaction)
        session.flush()
        rebuild_transaction_hash_chain(session)
        session.flush()
        return transaction.to_dict()


def update_transaction(transaction_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            return None

        current = transaction.to_dict()
        line_items_supplied = "line_items" in data
        if not line_items_supplied:
            data = {**data, "line_items": current.get("line_items") or []}
        source = {**current, **data}
        if line_items_supplied and "amount" not in data:
            source.pop("amount", None)
        payload = _transaction_payload(source, session)
        if payload["transaction_type"] == "EXPENSE":
            ensure_expense_within_item_cap(
                session,
                payload["budget_item_id"],
                payload["amount"],
                transaction_status=payload["transaction_status"],
                approval_status=payload["approval_status"],
                exclude_transaction_id=transaction_id,
            )
        for field in [
            "plan_id",
            "student_id",
            "approver_id",
            "budget_item_id",
            "amount",
            "amount_override_reason",
            "transaction_type",
            "transaction_status",
            "approval_status",
            "notes",
            "receipt_path",
        ]:
            setattr(transaction, field, payload[field])

        transaction.transaction_date = payload["transaction_date"]
        _replace_line_items(transaction, payload["line_items"])

        session.flush()
        rebuild_transaction_hash_chain(session)
        session.flush()
        return transaction.to_dict()


def delete_transaction(transaction_id: int) -> bool:
    with session_scope() as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            return False
        if transaction.approval_status != "Pending" or transaction.transaction_status == "Void":
            raise ValueError(
                f"Cannot delete transaction #{transaction_id} because it is not a pending active record. "
                "Set transaction status to Void instead."
            )
        session.delete(transaction)
        session.flush()
        rebuild_transaction_hash_chain(session)
        return True
