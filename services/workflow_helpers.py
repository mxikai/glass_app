from __future__ import annotations

from decimal import Decimal
from typing import Any

from models.budget_plan_model import BudgetPlan
from models.transaction_model import Transaction


def money_float(value: Any) -> float:
    return float(Decimal(str(value or 0)))


def is_official_transaction(transaction: Transaction) -> bool:
    return (
        transaction.transaction_status == "Active"
        and transaction.approval_status == "Approved"
    )


def select_active_or_latest_plan(session, plan_id: int | None = None) -> BudgetPlan | None:
    if plan_id:
        return session.get(BudgetPlan, plan_id)
    active_plans = (
        session.query(BudgetPlan)
        .filter(BudgetPlan.status == "Active")
        .order_by(BudgetPlan.plan_id)
        .all()
    )
    if active_plans:
        return active_plans[-1]
    plans = session.query(BudgetPlan).order_by(BudgetPlan.plan_id).all()
    return plans[-1] if plans else None


def expense_line_item_summary(transaction: Transaction) -> str:
    return "; ".join(
        f"{item.quantity} x {item.item_name} @ {money_float(item.unit_cost):,.2f}"
        for item in transaction.expense_line_items
    )
