from __future__ import annotations

from decimal import Decimal

from models.budget_item_model import BudgetItem
from models.fund_bucket_model import FundBucket
from models.transaction_model import Transaction


RESERVING_APPROVAL_STATUSES = ("Pending", "Approved")


def money_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def money_text(value) -> str:
    return f"PHP {money_decimal(value):,.2f}"


def _bucket_total(session, plan_id: int, *, exclude_bucket_id: int | None = None) -> Decimal:
    query = session.query(FundBucket).filter(FundBucket.plan_id == plan_id)
    if exclude_bucket_id is not None:
        query = query.filter(FundBucket.bucket_id != exclude_bucket_id)
    return sum((money_decimal(bucket.planned_amount) for bucket in query.all()), Decimal("0"))


def _item_total(session, bucket_id: int, *, exclude_item_id: int | None = None) -> Decimal:
    query = session.query(BudgetItem).filter(BudgetItem.bucket_id == bucket_id)
    if exclude_item_id is not None:
        query = query.filter(BudgetItem.budget_item_id != exclude_item_id)
    return sum((money_decimal(item.planned_amount) for item in query.all()), Decimal("0"))


def reserved_expense_total(
    session,
    budget_item_id: int,
    *,
    exclude_transaction_id: int | None = None,
) -> Decimal:
    query = session.query(Transaction).filter(
        Transaction.transaction_type == "EXPENSE",
        Transaction.transaction_status == "Active",
        Transaction.approval_status.in_(RESERVING_APPROVAL_STATUSES),
        Transaction.budget_item_id == budget_item_id,
    )
    if exclude_transaction_id is not None:
        query = query.filter(Transaction.transaction_id != exclude_transaction_id)
    return sum((money_decimal(transaction.amount) for transaction in query.all()), Decimal("0"))


def is_reserving_expense(transaction_status: str | None, approval_status: str | None) -> bool:
    return transaction_status == "Active" and approval_status in RESERVING_APPROVAL_STATUSES


def ensure_plan_covers_buckets(session, plan_id: int, planned_amount: Decimal) -> None:
    child_total = _bucket_total(session, plan_id)
    if child_total > planned_amount:
        raise ValueError(
            "Budget plan total cannot be lower than fund bucket allocations. "
            f"Plan cap: {money_text(planned_amount)}. "
            f"Fund buckets: {money_text(child_total)}."
        )


def ensure_bucket_allocation_within_plan(
    session,
    plan_id: int,
    planned_amount: Decimal,
    *,
    plan_amount: Decimal,
    exclude_bucket_id: int | None = None,
) -> None:
    next_total = _bucket_total(session, plan_id, exclude_bucket_id=exclude_bucket_id) + planned_amount
    if next_total > plan_amount:
        raise ValueError(
            "Fund bucket allocation exceeds the budget plan cap. "
            f"Plan cap: {money_text(plan_amount)}. "
            f"Fund buckets would total: {money_text(next_total)}."
        )


def ensure_bucket_covers_items(session, bucket_id: int, planned_amount: Decimal) -> None:
    child_total = _item_total(session, bucket_id)
    if child_total > planned_amount:
        raise ValueError(
            "Fund bucket amount cannot be lower than budget item allocations. "
            f"Bucket cap: {money_text(planned_amount)}. "
            f"Budget items: {money_text(child_total)}."
        )


def ensure_item_allocation_within_bucket(
    session,
    bucket_id: int,
    planned_amount: Decimal,
    *,
    bucket_amount: Decimal,
    exclude_item_id: int | None = None,
) -> None:
    next_total = _item_total(session, bucket_id, exclude_item_id=exclude_item_id) + planned_amount
    if next_total > bucket_amount:
        raise ValueError(
            "Budget item allocation exceeds the fund bucket cap. "
            f"Bucket cap: {money_text(bucket_amount)}. "
            f"Budget items would total: {money_text(next_total)}."
        )


def ensure_item_covers_reserved_expenses(
    session,
    budget_item_id: int,
    planned_amount: Decimal,
) -> None:
    reserved = reserved_expense_total(session, budget_item_id)
    if reserved > planned_amount:
        raise ValueError(
            "Budget item amount cannot be lower than reserved expenses. "
            f"Item cap: {money_text(planned_amount)}. "
            f"Reserved expenses: {money_text(reserved)}."
        )


def ensure_expense_within_item_cap(
    session,
    budget_item_id: int,
    amount: Decimal,
    *,
    transaction_status: str | None,
    approval_status: str | None,
    exclude_transaction_id: int | None = None,
) -> None:
    if not is_reserving_expense(transaction_status, approval_status):
        return

    item = session.get(BudgetItem, budget_item_id)
    if not item:
        raise ValueError("Invalid budget_item_id")

    cap = money_decimal(item.planned_amount)
    existing = reserved_expense_total(
        session,
        budget_item_id,
        exclude_transaction_id=exclude_transaction_id,
    )
    next_total = existing + amount
    if next_total > cap:
        remaining = cap - existing
        raise ValueError(
            "Expense exceeds the budget item cap. "
            f"Item cap: {money_text(cap)}. "
            f"Reserved expenses would total: {money_text(next_total)}. "
            f"Remaining: {money_text(max(remaining, Decimal('0')))}."
        )
