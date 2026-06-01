from __future__ import annotations

from datetime import datetime

from models.budget_item_model import BudgetItem
from models.budget_plan_model import BudgetPlan
from models.student_model import Student
from models.transaction_model import Transaction
from utils.db import session_scope
from utils.validators import require_fields


def _parse_datetime(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


# Transactions

def list_transactions() -> list[dict]:
    with session_scope() as session:
        transactions = session.query(Transaction).all()
        return [transaction.to_dict() for transaction in transactions]


def get_transaction(transaction_id: int) -> dict | None:
    with session_scope() as session:
        transaction = session.get(Transaction, transaction_id)
        return transaction.to_dict() if transaction else None


def create_transaction(data: dict) -> dict:
    require_fields(data, ["plan_id", "amount", "transaction_type"])

    transaction_type = str(data["transaction_type"]).upper()
    if transaction_type not in {"PAYMENT", "EXPENSE"}:
        raise ValueError("transaction_type must be PAYMENT or EXPENSE")

    if transaction_type == "PAYMENT":
        require_fields(data, ["student_id"])
    if transaction_type == "EXPENSE":
        require_fields(data, ["budget_item_id"])

    with session_scope() as session:
        plan = session.get(BudgetPlan, data["plan_id"])
        if not plan:
            raise ValueError("Invalid plan_id")

        if data.get("student_id"):
            if not session.get(Student, data["student_id"]):
                raise ValueError("Invalid student_id")

        if data.get("budget_item_id"):
            if not session.get(BudgetItem, data["budget_item_id"]):
                raise ValueError("Invalid budget_item_id")

        transaction = Transaction(
            plan_id=data["plan_id"],
            student_id=data.get("student_id"),
            approver_id=data.get("approver_id"),
            budget_item_id=data.get("budget_item_id"),
            amount=data["amount"],
            transaction_type=transaction_type,
            transaction_status=data.get("transaction_status", "Active"),
            approval_status=data.get("approval_status", "Pending"),
            transaction_date=_parse_datetime(data.get("transaction_date")),
            notes=data.get("notes"),
            receipt_path=data.get("receipt_path"),
            current_hash=data.get("current_hash"),
            previous_hash=data.get("previous_hash"),
        )

        session.add(transaction)
        session.flush()
        return transaction.to_dict()


def update_transaction(transaction_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            return None

        for field in [
            "plan_id",
            "student_id",
            "approver_id",
            "budget_item_id",
            "amount",
            "transaction_type",
            "transaction_status",
            "approval_status",
            "notes",
            "receipt_path",
            "current_hash",
            "previous_hash",
        ]:
            if field in data:
                setattr(transaction, field, data[field])

        if "transaction_date" in data:
            transaction.transaction_date = _parse_datetime(data.get("transaction_date"))

        session.flush()
        return transaction.to_dict()


def delete_transaction(transaction_id: int) -> bool:
    with session_scope() as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            return False
        session.delete(transaction)
        return True
