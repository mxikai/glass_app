from __future__ import annotations

from models.budget_item_model import BudgetItem
from models.fund_bucket_model import FundBucket
from models.inventory_model import InventoryItem
from models.transaction_model import Transaction
from models.student_model import Student
from utils.db import session_scope
from services.workflow_helpers import (
    is_official_transaction,
    money_float,
    select_active_or_latest_plan,
)


def get_dashboard_summary(plan_id: int | None = None) -> dict:
    with session_scope() as session:
        plan = select_active_or_latest_plan(session, plan_id)
        if not plan:
            return {
                "active_plan": None,
                "collection_progress": {"paid_count": 0, "pending_count": 0, "paid_student_ids": [], "pending_student_ids": []},
                "cash_flow": [],
                "totals": {"payments": 0.0, "expenses": 0.0, "available_funds": 0.0},
                "fund_bucket_utilization": [],
                "budget_item_spending": [],
                "inventory_summary": {"total_items": 0, "total_quantity": 0, "by_condition": {}, "items": []},
            }

        transactions = (
            session.query(Transaction)
            .filter(Transaction.plan_id == plan.plan_id)
            .order_by(Transaction.transaction_date, Transaction.transaction_id)
            .all()
        )
        official_transactions = [row for row in transactions if is_official_transaction(row)]
        payments = [row for row in official_transactions if row.transaction_type == "PAYMENT"]
        expenses = [row for row in official_transactions if row.transaction_type == "EXPENSE"]
        payment_total = sum((money_float(row.amount) for row in payments), 0.0)
        expense_total = sum((money_float(row.amount) for row in expenses), 0.0)

        paid_student_ids = sorted(list({row.student_id for row in payments if row.student_id}))
        active_students = session.query(Student).filter(Student.status.notin_(["Inactive", "Alumni"])).all()
        active_student_ids = [s.student_id for s in active_students]
        
        pending_student_ids = [s_id for s_id in active_student_ids if s_id not in paid_student_ids]
        
        running_balance = 0.0
        cash_flow = []
        for transaction in official_transactions:
            signed_amount = money_float(transaction.amount)
            if transaction.transaction_type == "EXPENSE":
                signed_amount = -signed_amount
            running_balance += signed_amount
            cash_flow.append(
                {
                    "transaction_id": transaction.transaction_id,
                    "transaction_date": transaction.transaction_date.isoformat()
                    if transaction.transaction_date
                    else None,
                    "transaction_type": transaction.transaction_type,
                    "amount": abs(signed_amount),
                    "signed_amount": signed_amount,
                    "running_balance": running_balance,
                }
            )

        buckets = (
            session.query(FundBucket)
            .filter(FundBucket.plan_id == plan.plan_id)
            .order_by(FundBucket.bucket_id)
            .all()
        )
        items = (
            session.query(BudgetItem)
            .join(FundBucket)
            .filter(FundBucket.plan_id == plan.plan_id)
            .order_by(BudgetItem.budget_item_id)
            .all()
        )
        expense_by_item: dict[int, float] = {}
        for expense in expenses:
            if expense.budget_item_id is not None:
                expense_by_item[expense.budget_item_id] = (
                    expense_by_item.get(expense.budget_item_id, 0.0) + money_float(expense.amount)
                )

        budget_item_spending = []
        for item in items:
            spent = expense_by_item.get(item.budget_item_id, 0.0)
            planned = money_float(item.planned_amount)
            remaining = planned - spent
            budget_item_spending.append(
                {
                    "budget_item_id": item.budget_item_id,
                    "bucket_id": item.bucket_id,
                    "item_name": item.item_name,
                    "planned_amount": planned,
                    "spent_amount": spent,
                    "remaining_amount": remaining,
                    "spending_status": "Over" if spent > planned else "Within",
                }
            )

        item_bucket = {item.budget_item_id: item.bucket_id for item in items}
        expense_by_bucket: dict[int, float] = {}
        for item_id, spent in expense_by_item.items():
            bucket_id = item_bucket.get(item_id)
            if bucket_id is not None:
                expense_by_bucket[bucket_id] = expense_by_bucket.get(bucket_id, 0.0) + spent

        fund_bucket_utilization = []
        for bucket in buckets:
            spent = expense_by_bucket.get(bucket.bucket_id, 0.0)
            planned = money_float(bucket.planned_amount)
            fund_bucket_utilization.append(
                {
                    "bucket_id": bucket.bucket_id,
                    "bucket_name": bucket.bucket_name,
                    "planned_amount": planned,
                    "spent_amount": spent,
                    "remaining_amount": planned - spent,
                }
            )

        plan_transaction_ids = {transaction.transaction_id for transaction in transactions}
        inventory_items = session.query(InventoryItem).order_by(InventoryItem.inventory_item_id).all()
        scoped_inventory = [
            item
            for item in inventory_items
            if item.source_type == "Legacy" or item.transaction_id in plan_transaction_ids
        ]
        condition_counts: dict[str, int] = {}
        for item in scoped_inventory:
            condition = item.item_condition or "Unspecified"
            condition_counts[condition] = condition_counts.get(condition, 0) + 1

        return {
            "active_plan": plan.to_dict(),
            "collection_progress": {
                "paid_count": len(paid_student_ids),
                "pending_count": len(pending_student_ids),
                "paid_student_ids": paid_student_ids,
                "pending_student_ids": pending_student_ids,
            },
            "cash_flow": cash_flow,
            "totals": {
                "payments": payment_total,
                "expenses": expense_total,
                "available_funds": payment_total - expense_total,
            },
            "fund_bucket_utilization": fund_bucket_utilization,
            "budget_item_spending": budget_item_spending,
            "inventory_summary": {
                "total_items": len(scoped_inventory),
                "total_quantity": sum(item.quantity or 0 for item in scoped_inventory),
                "by_condition": condition_counts,
                "items": [item.to_dict() for item in scoped_inventory],
            },
        }
