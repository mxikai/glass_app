from __future__ import annotations

from datetime import date
from decimal import Decimal

from models.budget_item_model import BudgetItem
from models.budget_plan_model import BudgetPlan
from models.fund_bucket_model import FundBucket
from models.student_model import Student
from utils.db import session_scope
from utils.validators import require_fields


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _compute_fee(total_planned_budget, member_count) -> Decimal:
    if member_count is None or int(member_count) <= 0:
        raise ValueError("member_count must be greater than 0")
    return _to_decimal(total_planned_budget) / Decimal(str(member_count))


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
    require_fields(data, ["academic_year", "semester", "total_planned_budget", "member_count"])

    total_planned_budget = _to_decimal(data["total_planned_budget"])
    member_count = int(data["member_count"])

    semestral_fee_amount = _to_decimal(data.get("semestral_fee_amount"))
    if semestral_fee_amount is None:
        semestral_fee_amount = _compute_fee(total_planned_budget, member_count)

    with session_scope() as session:
        plan = BudgetPlan(
            academic_year=data["academic_year"],
            semester=data["semester"],
            total_planned_budget=total_planned_budget,
            member_count=member_count,
            semestral_fee_amount=semestral_fee_amount,
            approval_status=data.get("approval_status", "Pending"),
            approved_date=_parse_date(data.get("approved_date")),
            status=data.get("status", "Active"),
        )

        student_ids = data.get("student_ids") or []
        if student_ids:
            students = (
                session.query(Student)
                .filter(Student.student_id.in_(student_ids))
                .all()
            )
            if len(students) != len(set(student_ids)):
                raise ValueError("One or more student_ids are invalid")
            plan.students = students

        session.add(plan)
        session.flush()
        return plan.to_dict()


def update_budget_plan(plan_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        plan = session.get(BudgetPlan, plan_id)
        if not plan:
            return None

        for field in ["academic_year", "semester", "approval_status", "status"]:
            if field in data:
                setattr(plan, field, data[field])

        if "approved_date" in data:
            plan.approved_date = _parse_date(data.get("approved_date"))

        if "total_planned_budget" in data:
            plan.total_planned_budget = _to_decimal(data.get("total_planned_budget"))

        if "member_count" in data:
            plan.member_count = int(data.get("member_count"))

        if "semestral_fee_amount" in data:
            plan.semestral_fee_amount = _to_decimal(data.get("semestral_fee_amount"))
        elif "total_planned_budget" in data or "member_count" in data:
            plan.semestral_fee_amount = _compute_fee(plan.total_planned_budget, plan.member_count)

        if "student_ids" in data:
            student_ids = data.get("student_ids") or []
            students = (
                session.query(Student)
                .filter(Student.student_id.in_(student_ids))
                .all()
            )
            if len(students) != len(set(student_ids)):
                raise ValueError("One or more student_ids are invalid")
            plan.students = students

        session.flush()
        return plan.to_dict()


def delete_budget_plan(plan_id: int) -> bool:
    with session_scope() as session:
        plan = session.get(BudgetPlan, plan_id)
        if not plan:
            return False
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
    require_fields(data, ["plan_id", "bucket_name", "planned_amount"])

    with session_scope() as session:
        plan = session.get(BudgetPlan, data["plan_id"])
        if not plan:
            raise ValueError("Invalid plan_id")

        bucket = FundBucket(
            plan_id=data["plan_id"],
            bucket_name=data["bucket_name"],
            planned_amount=_to_decimal(data["planned_amount"]),
            description=data.get("description"),
        )
        session.add(bucket)
        session.flush()
        return bucket.to_dict()


def update_fund_bucket(bucket_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        bucket = session.get(FundBucket, bucket_id)
        if not bucket:
            return None

        for field in ["bucket_name", "description"]:
            if field in data:
                setattr(bucket, field, data[field])

        if "planned_amount" in data:
            bucket.planned_amount = _to_decimal(data.get("planned_amount"))

        session.flush()
        return bucket.to_dict()


def delete_fund_bucket(bucket_id: int) -> bool:
    with session_scope() as session:
        bucket = session.get(FundBucket, bucket_id)
        if not bucket:
            return False
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
    require_fields(data, ["bucket_id", "item_name", "planned_amount"])

    with session_scope() as session:
        bucket = session.get(FundBucket, data["bucket_id"])
        if not bucket:
            raise ValueError("Invalid bucket_id")

        item = BudgetItem(
            bucket_id=data["bucket_id"],
            item_name=data["item_name"],
            item_type=data.get("item_type"),
            planned_amount=_to_decimal(data["planned_amount"]),
            description=data.get("description"),
        )
        session.add(item)
        session.flush()
        return item.to_dict()


def update_budget_item(item_id: int, data: dict) -> dict | None:
    with session_scope() as session:
        item = session.get(BudgetItem, item_id)
        if not item:
            return None

        for field in ["item_name", "item_type", "description"]:
            if field in data:
                setattr(item, field, data[field])

        if "planned_amount" in data:
            item.planned_amount = _to_decimal(data.get("planned_amount"))

        session.flush()
        return item.to_dict()


def delete_budget_item(item_id: int) -> bool:
    with session_scope() as session:
        item = session.get(BudgetItem, item_id)
        if not item:
            return False
        session.delete(item)
        return True
