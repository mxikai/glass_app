from __future__ import annotations

from backend.models.budget_item_model import BudgetItem
from backend.models.budget_plan_model import BudgetPlan
from backend.models.student_model import Student
from backend.models.transaction_model import Transaction
from backend.utils.db import session_scope
from backend.utils.validators import (
    APPROVAL_STATUSES,
    TRANSACTION_STATUSES,
    TRANSACTION_TYPES,
    choice_value,
    decimal_value,
    int_value,
    iso_datetime_value,
    optional_student_id_value,
    sha256_value,
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
        student_id = student_id_value(data.get("student_id"))
        if budget_item_id is not None:
            raise ValueError("PAYMENT transactions cannot include budget_item_id")
        student = session.get(Student, student_id)
        if not student:
            raise ValueError("Invalid student_id")
        plan_student_ids = {student.student_id for student in plan.students}
        if student_id not in plan_student_ids:
            raise ValueError("student_id must belong to the selected plan")
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

    approver_id = _eligible_approver(session, data.get("approver_id"), approval_status or "Pending")
    return {
        "plan_id": plan_id,
        "student_id": student_id,
        "approver_id": approver_id,
        "budget_item_id": budget_item_id,
        "amount": decimal_value(data.get("amount"), "amount"),
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
        "current_hash": sha256_value(data.get("current_hash"), "current_hash"),
        "previous_hash": sha256_value(data.get("previous_hash"), "previous_hash"),
    }


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
    with session_scope() as session:
        payload = _transaction_payload(data, session)
        transaction = Transaction(
            plan_id=payload["plan_id"],
            student_id=payload["student_id"],
            approver_id=payload["approver_id"],
            budget_item_id=payload["budget_item_id"],
            amount=payload["amount"],
            transaction_type=payload["transaction_type"],
            transaction_status=payload["transaction_status"],
            approval_status=payload["approval_status"],
            transaction_date=payload["transaction_date"],
            notes=payload["notes"],
            receipt_path=payload["receipt_path"],
            current_hash=payload["current_hash"],
            previous_hash=payload["previous_hash"],
        )

        session.add(transaction)
        session.flush()
        return transaction.to_dict()


def update_transaction(transaction_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            return None

        current = transaction.to_dict()
        payload = _transaction_payload({**current, **data}, session)
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
            setattr(transaction, field, payload[field])

        transaction.transaction_date = payload["transaction_date"]

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
        return True
