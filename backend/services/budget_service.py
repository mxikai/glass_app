from __future__ import annotations

from decimal import Decimal

from models.budget_item_model import BudgetItem
from models.budget_plan_model import BudgetPlan
from models.fund_bucket_model import FundBucket
from models.student_model import Student
from models.transaction_model import Transaction
from services.budget_cap_service import (
    ensure_bucket_allocation_within_plan,
    ensure_bucket_covers_items,
    ensure_item_allocation_within_bucket,
    ensure_item_covers_reserved_expenses,
    ensure_plan_covers_buckets,
)
from utils.db import session_scope
from utils.validators import (
    APPROVAL_STATUSES,
    PLAN_STATUSES,
    SEMESTERS,
    academic_year_value,
    choice_value,
    decimal_value,
    int_value,
    iso_date_value,
    optional_student_id_value,
    text_value,
)


def _compute_fee(total_planned_budget, member_count) -> Decimal:
    if member_count is None or int(member_count) <= 0:
        raise ValueError("member_count must be greater than 0")
    return Decimal(str(total_planned_budget)) / Decimal(str(member_count))


def _student_ids_value(value, *, required: bool = False) -> list[str]:
    if value is None:
        if required:
            raise ValueError("student_ids is required")
        return []
    if not isinstance(value, list):
        raise ValueError("student_ids must be a list")
    student_ids = [optional_student_id_value(item) for item in value]
    normalized = [student_id for student_id in student_ids if student_id]
    if len(normalized) != len(student_ids):
        raise ValueError("student_ids cannot include blank values")
    if len(normalized) != len(set(normalized)):
        raise ValueError("student_ids cannot include duplicates")
    return normalized


def _load_students(session, student_ids: list[str]) -> list[Student]:
    if not student_ids:
        return []
    students = (
        session.query(Student)
        .filter(Student.student_id.in_(student_ids))
        .all()
    )
    if len(students) != len(set(student_ids)):
        raise ValueError("One or more student_ids are invalid")
    return students


def _validate_plan_payload(
    data: dict,
    *,
    current: dict | None = None,
    allow_missing_student_ids: bool = True,
) -> dict:
    source = {**(current or {}), **data}
    student_ids = _student_ids_value(
        source.get("student_ids"),
        required=not allow_missing_student_ids,
    )
    member_count = int_value(
        source.get("member_count"),
        "member_count",
        min_value=1,
    )
    if "student_ids" in source and member_count != len(student_ids):
        raise ValueError("member_count must match the number of student_ids")

    total_planned_budget = decimal_value(
        source.get("total_planned_budget"),
        "total_planned_budget",
    )
    semestral_fee_amount = decimal_value(
        source.get("semestral_fee_amount"),
        "semestral_fee_amount",
        required=False,
    )
    if semestral_fee_amount is None:
        semestral_fee_amount = _compute_fee(total_planned_budget, member_count)

    return {
        "academic_year": academic_year_value(source.get("academic_year")),
        "semester": choice_value(source.get("semester"), "semester", SEMESTERS),
        "total_planned_budget": total_planned_budget,
        "member_count": member_count,
        "semestral_fee_amount": semestral_fee_amount,
        "approval_status": choice_value(
            source.get("approval_status"),
            "approval_status",
            APPROVAL_STATUSES,
            default="Pending",
        ),
        "approved_date": iso_date_value(
            source.get("approved_date"),
            "approved_date",
            no_future=True,
        ),
        "status": choice_value(
            source.get("status"),
            "status",
            PLAN_STATUSES,
            default="Active",
        ),
        "student_ids": student_ids,
    }


def _bucket_payload(data: dict, *, current: dict | None = None) -> dict:
    source = {**(current or {}), **data}
    return {
        "bucket_name": text_value(source.get("bucket_name"), "bucket_name", required=True, max_length=120),
        "planned_amount": decimal_value(source.get("planned_amount"), "planned_amount"),
        "description": text_value(source.get("description"), "description", max_length=255),
    }


def _item_payload(data: dict, *, current: dict | None = None) -> dict:
    source = {**(current or {}), **data}
    return {
        "item_name": text_value(source.get("item_name"), "item_name", required=True, max_length=120),
        "item_type": text_value(source.get("item_type"), "item_type", max_length=50),
        "planned_amount": decimal_value(source.get("planned_amount"), "planned_amount"),
        "description": text_value(source.get("description"), "description", max_length=255),
    }


# Budget plans

def list_budget_plans() -> list[dict]:
    with session_scope() as session:
        plans = session.query(BudgetPlan).all()
        return [plan.to_dict() for plan in plans]


def get_budget_plan(plan_id: int) -> dict | None:
    with session_scope() as session:
        plan = session.get(BudgetPlan, plan_id)
        return plan.to_dict() if plan else None


def create_budget_plan(data: dict) -> dict:
    payload = _validate_plan_payload(data)

    with session_scope() as session:
        plan = BudgetPlan(
            academic_year=payload["academic_year"],
            semester=payload["semester"],
            total_planned_budget=payload["total_planned_budget"],
            member_count=payload["member_count"],
            semestral_fee_amount=payload["semestral_fee_amount"],
            approval_status=payload["approval_status"],
            approved_date=payload["approved_date"],
            status=payload["status"],
        )

        student_ids = payload["student_ids"]
        if student_ids:
            plan.students = _load_students(session, student_ids)

        session.add(plan)
        session.flush()
        return plan.to_dict()


def update_budget_plan(plan_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        plan = session.get(BudgetPlan, plan_id)
        if not plan:
            return None

        current = plan.to_dict()
        payload = _validate_plan_payload(data, current=current)
        if "semestral_fee_amount" not in data and (
            "total_planned_budget" in data or "member_count" in data
        ):
            payload["semestral_fee_amount"] = _compute_fee(
                payload["total_planned_budget"],
                payload["member_count"],
            )

        if "student_ids" in data:
            student_ids = payload["student_ids"]
            removed_ids = set(current.get("student_ids") or []) - set(student_ids)
            if removed_ids:
                transaction_count = (
                    session.query(Transaction)
                    .filter(
                        Transaction.plan_id == plan_id,
                        Transaction.student_id.in_(removed_ids),
                    )
                    .count()
                )
                if transaction_count:
                    raise ValueError(
                        "Cannot remove student(s) from this plan because they already "
                        f"have {transaction_count} transaction(s) in it."
                    )
            students = _load_students(session, student_ids)
            plan.students = students

        ensure_plan_covers_buckets(session, plan_id, payload["total_planned_budget"])

        for field in [
            "academic_year",
            "semester",
            "total_planned_budget",
            "member_count",
            "semestral_fee_amount",
            "approval_status",
            "approved_date",
            "status",
        ]:
            setattr(plan, field, payload[field])

        session.flush()
        return plan.to_dict()


def delete_budget_plan(plan_id: int) -> bool:
    with session_scope() as session:
        plan = session.get(BudgetPlan, plan_id)
        if not plan:
            return False
        transaction_count = (
            session.query(Transaction)
            .filter(Transaction.plan_id == plan_id)
            .count()
        )
        if transaction_count:
            raise ValueError(
                f"Cannot delete plan #{plan_id} because it has {transaction_count} "
                "transaction(s). Set status to Archived instead."
            )
        session.delete(plan)
        return True


# Fund buckets

def list_fund_buckets() -> list[dict]:
    with session_scope() as session:
        buckets = session.query(FundBucket).all()
        return [bucket.to_dict() for bucket in buckets]


def get_fund_bucket(bucket_id: int) -> dict | None:
    with session_scope() as session:
        bucket = session.get(FundBucket, bucket_id)
        return bucket.to_dict() if bucket else None


def create_fund_bucket(data: dict) -> dict:
    plan_id = int_value(data.get("plan_id"), "plan_id", min_value=1)
    payload = _bucket_payload(data)

    with session_scope() as session:
        plan = session.get(BudgetPlan, plan_id)
        if not plan:
            raise ValueError("Invalid plan_id")
        ensure_bucket_allocation_within_plan(
            session,
            plan_id,
            payload["planned_amount"],
            plan_amount=plan.total_planned_budget,
        )

        bucket = FundBucket(
            plan_id=plan_id,
            bucket_name=payload["bucket_name"],
            planned_amount=payload["planned_amount"],
            description=payload["description"],
        )
        session.add(bucket)
        session.flush()
        return bucket.to_dict()


def update_fund_bucket(bucket_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        bucket = session.get(FundBucket, bucket_id)
        if not bucket:
            return None

        payload = _bucket_payload(data, current=bucket.to_dict())
        ensure_bucket_allocation_within_plan(
            session,
            bucket.plan_id,
            payload["planned_amount"],
            plan_amount=bucket.budget_plan.total_planned_budget,
            exclude_bucket_id=bucket.bucket_id,
        )
        ensure_bucket_covers_items(session, bucket.bucket_id, payload["planned_amount"])
        for field in ["bucket_name", "planned_amount", "description"]:
            setattr(bucket, field, payload[field])

        session.flush()
        return bucket.to_dict()


def delete_fund_bucket(bucket_id: int) -> bool:
    with session_scope() as session:
        bucket = session.get(FundBucket, bucket_id)
        if not bucket:
            return False
        item_ids = [item.budget_item_id for item in bucket.budget_items]
        transaction_count = 0
        if item_ids:
            transaction_count = (
                session.query(Transaction)
                .filter(Transaction.budget_item_id.in_(item_ids))
                .count()
            )
        if transaction_count:
            raise ValueError(
                f"Cannot delete bucket #{bucket_id} because its items have "
                f"{transaction_count} transaction(s). Delete or void those records first."
            )
        session.delete(bucket)
        return True


# Budget items

def list_budget_items() -> list[dict]:
    with session_scope() as session:
        items = session.query(BudgetItem).all()
        return [item.to_dict() for item in items]


def get_budget_item(item_id: int) -> dict | None:
    with session_scope() as session:
        item = session.get(BudgetItem, item_id)
        return item.to_dict() if item else None


def create_budget_item(data: dict) -> dict:
    bucket_id = int_value(data.get("bucket_id"), "bucket_id", min_value=1)
    payload = _item_payload(data)

    with session_scope() as session:
        bucket = session.get(FundBucket, bucket_id)
        if not bucket:
            raise ValueError("Invalid bucket_id")
        ensure_item_allocation_within_bucket(
            session,
            bucket_id,
            payload["planned_amount"],
            bucket_amount=bucket.planned_amount,
        )

        item = BudgetItem(
            bucket_id=bucket_id,
            item_name=payload["item_name"],
            item_type=payload["item_type"],
            planned_amount=payload["planned_amount"],
            description=payload["description"],
        )
        session.add(item)
        session.flush()
        return item.to_dict()


def update_budget_item(item_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        item = session.get(BudgetItem, item_id)
        if not item:
            return None

        payload = _item_payload(data, current=item.to_dict())
        ensure_item_allocation_within_bucket(
            session,
            item.bucket_id,
            payload["planned_amount"],
            bucket_amount=item.fund_bucket.planned_amount,
            exclude_item_id=item.budget_item_id,
        )
        ensure_item_covers_reserved_expenses(
            session,
            item.budget_item_id,
            payload["planned_amount"],
        )
        for field in ["item_name", "item_type", "planned_amount", "description"]:
            setattr(item, field, payload[field])

        session.flush()
        return item.to_dict()


def delete_budget_item(item_id: int) -> bool:
    with session_scope() as session:
        item = session.get(BudgetItem, item_id)
        if not item:
            return False
        transaction_count = (
            session.query(Transaction)
            .filter(Transaction.budget_item_id == item_id)
            .count()
        )
        if transaction_count:
            raise ValueError(
                f"Cannot delete budget item #{item_id} because it has "
                f"{transaction_count} transaction(s)."
            )
        session.delete(item)
        return True
