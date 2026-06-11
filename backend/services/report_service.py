from __future__ import annotations

from io import BytesIO

from models.budget_item_model import BudgetItem
from models.budget_plan_model import BudgetPlan
from models.fund_bucket_model import FundBucket
from models.inventory_model import InventoryItem
from models.student_model import Student
from models.transaction_model import Transaction
from services.dashboard_service import get_dashboard_summary
from services.workflow_helpers import expense_line_item_summary, select_active_or_latest_plan
from utils.db import session_scope


REPORT_TYPES = (
    "budget-plan",
    "collection",
    "expense",
    "inventory",
    "transparency",
)


def _validate_report_type(report_type: str) -> str:
    normalized = (report_type or "").strip().lower()
    if normalized not in REPORT_TYPES:
        raise ValueError(f"report_type must be one of: {', '.join(REPORT_TYPES)}")
    return normalized


def _student_name_map(session) -> dict[str, str]:
    return {student.student_id: student.name for student in session.query(Student).all()}


def _line_item_summary(transaction: Transaction) -> str:
    return expense_line_item_summary(transaction)


def _budget_plan_report(session, plan: BudgetPlan) -> dict:
    buckets = (
        session.query(FundBucket)
        .filter(FundBucket.plan_id == plan.plan_id)
        .order_by(FundBucket.bucket_id)
        .all()
    )
    bucket_ids = [bucket.bucket_id for bucket in buckets]
    items = []
    if bucket_ids:
        items = (
            session.query(BudgetItem)
            .filter(BudgetItem.bucket_id.in_(bucket_ids))
            .order_by(BudgetItem.budget_item_id)
            .all()
        )
    return {
        "plan": plan.to_dict(),
        "fund_buckets": [bucket.to_dict() for bucket in buckets],
        "budget_items": [item.to_dict() for item in items],
    }


def _collection_report(session, plan: BudgetPlan, summary: dict) -> dict:
    students_by_id = {student.student_id: student for student in plan.students}
    paid_ids = set(summary["collection_progress"]["paid_student_ids"])
    pending_ids = set(summary["collection_progress"]["pending_student_ids"])
    transactions = (
        session.query(Transaction)
        .filter(Transaction.plan_id == plan.plan_id, Transaction.transaction_type == "PAYMENT")
        .order_by(Transaction.transaction_date, Transaction.transaction_id)
        .all()
    )
    payments_by_student: dict[str, list[dict]] = {}
    for transaction in transactions:
        if transaction.student_id:
            payments_by_student.setdefault(transaction.student_id, []).append(transaction.to_dict())
    return {
        "plan": plan.to_dict(),
        "paid_students": [
            {
                "student_id": student_id,
                "name": students_by_id.get(student_id).name if students_by_id.get(student_id) else "",
                "payments": payments_by_student.get(student_id, []),
            }
            for student_id in sorted(paid_ids)
        ],
        "pending_students": [
            {
                "student_id": student_id,
                "name": students_by_id.get(student_id).name if students_by_id.get(student_id) else "",
            }
            for student_id in sorted(pending_ids)
        ],
    }


def _expense_report(session, plan: BudgetPlan) -> dict:
    items = {
        item.budget_item_id: item
        for item in session.query(BudgetItem).join(FundBucket).filter(FundBucket.plan_id == plan.plan_id).all()
    }
    buckets = {
        bucket.bucket_id: bucket
        for bucket in session.query(FundBucket).filter(FundBucket.plan_id == plan.plan_id).all()
    }
    transactions = (
        session.query(Transaction)
        .filter(Transaction.plan_id == plan.plan_id, Transaction.transaction_type == "EXPENSE")
        .order_by(Transaction.transaction_date, Transaction.transaction_id)
        .all()
    )
    rows = []
    for transaction in transactions:
        item = items.get(transaction.budget_item_id)
        bucket = buckets.get(item.bucket_id) if item else None
        transaction_dict = transaction.to_dict()
        rows.append(
            {
                **transaction_dict,
                "bucket_id": bucket.bucket_id if bucket else None,
                "bucket_name": bucket.bucket_name if bucket else "",
                "budget_item_name": item.item_name if item else "",
                "line_item_summary": _line_item_summary(transaction),
            }
        )
    return {"plan": plan.to_dict(), "expenses": rows}


def _inventory_report(session, plan: BudgetPlan) -> dict:
    plan_transaction_ids = {
        row.transaction_id
        for row in session.query(Transaction).filter(Transaction.plan_id == plan.plan_id).all()
    }
    items = session.query(InventoryItem).order_by(InventoryItem.inventory_item_id).all()
    scoped = [
        item
        for item in items
        if item.source_type == "Legacy" or item.transaction_id in plan_transaction_ids
    ]
    return {"plan": plan.to_dict(), "inventory_items": [item.to_dict() for item in scoped]}


def get_report_data(report_type: str, plan_id: int | None = None) -> dict:
    report_type = _validate_report_type(report_type)
    summary = get_dashboard_summary(plan_id)
    with session_scope() as session:
        plan = select_active_or_latest_plan(session, plan_id)
        if not plan:
            raise ValueError("No budget plan found")

        if report_type == "budget-plan":
            data = _budget_plan_report(session, plan)
        elif report_type == "collection":
            data = _collection_report(session, plan, summary)
        elif report_type == "expense":
            data = _expense_report(session, plan)
        elif report_type == "inventory":
            data = _inventory_report(session, plan)
        else:
            data = {
                "budget_plan": _budget_plan_report(session, plan),
                "collection": _collection_report(session, plan, summary),
                "expense": _expense_report(session, plan),
                "inventory": _inventory_report(session, plan),
                "dashboard_summary": summary,
            }
        data["report_type"] = report_type
        data["student_names"] = _student_name_map(session)
        return data


def _flatten_rows(rows: list[dict], preferred_keys: list[str]) -> list[list[str]]:
    output = [preferred_keys]
    for row in rows:
        output.append([str(row.get(key, "")) for key in preferred_keys])
    return output


def _add_table(elements, rows: list[list[str]], table_class) -> None:
    from reportlab.platypus import TableStyle

    if len(rows) == 1:
        rows.append(["No records"] + [""] * (len(rows[0]) - 1))
    table = table_class(rows, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), "#e8eef8"),
            ("GRID", (0, 0), (-1, -1), 0.25, "#9aa6b2"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elements.append(table)


def generate_report_pdf(report_type: str, plan_id: int | None = None) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table
    from reportlab.lib.styles import getSampleStyleSheet

    data = get_report_data(report_type, plan_id)
    styles = getSampleStyleSheet()
    buffer = BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=letter, title=f"GLASS {report_type} report")
    elements = [
        Paragraph(f"GLASS {data['report_type'].replace('-', ' ').title()} Report", styles["Title"]),
        Spacer(1, 12),
    ]

    plan = data.get("plan") or data.get("budget_plan", {}).get("plan") or {}
    if plan:
        _add_table(
            elements,
            _flatten_rows(
                [plan],
                ["plan_id", "academic_year", "semester", "total_planned_budget", "member_count", "semestral_fee_amount", "approval_status", "status"],
            ),
            Table,
        )
        elements.append(Spacer(1, 12))

    if data["report_type"] == "budget-plan":
        elements.append(Paragraph("Fund Buckets", styles["Heading2"]))
        _add_table(elements, _flatten_rows(data["fund_buckets"], ["bucket_id", "bucket_name", "planned_amount", "description"]), Table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Budget Items", styles["Heading2"]))
        _add_table(elements, _flatten_rows(data["budget_items"], ["budget_item_id", "bucket_id", "item_name", "item_type", "planned_amount"]), Table)
    elif data["report_type"] == "collection":
        elements.append(Paragraph("Paid Students", styles["Heading2"]))
        _add_table(elements, _flatten_rows(data["paid_students"], ["student_id", "name"]), Table)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Pending Students", styles["Heading2"]))
        _add_table(elements, _flatten_rows(data["pending_students"], ["student_id", "name"]), Table)
    elif data["report_type"] == "expense":
        elements.append(Paragraph("Expenses", styles["Heading2"]))
        _add_table(
            elements,
            _flatten_rows(
                data["expenses"],
                ["transaction_id", "bucket_name", "budget_item_name", "line_item_summary", "amount", "approval_status", "transaction_status", "receipt_path"],
            ),
            Table,
        )
    elif data["report_type"] == "inventory":
        elements.append(Paragraph("Inventory", styles["Heading2"]))
        _add_table(
            elements,
            _flatten_rows(
                data["inventory_items"],
                ["inventory_item_id", "source_type", "transaction_id", "item_name", "quantity", "unit_cost", "item_condition", "status"],
            ),
            Table,
        )
    else:
        elements.append(Paragraph("Transparency Summary", styles["Heading2"]))
        summary = data["dashboard_summary"]
        rows = [
            {"metric": "Payments", "value": summary["totals"]["payments"]},
            {"metric": "Expenses", "value": summary["totals"]["expenses"]},
            {"metric": "Available Funds", "value": summary["totals"]["available_funds"]},
            {"metric": "Paid Students", "value": summary["collection_progress"]["paid_count"]},
            {"metric": "Pending Students", "value": summary["collection_progress"]["pending_count"]},
        ]
        _add_table(elements, _flatten_rows(rows, ["metric", "value"]), Table)

    document.build(elements)
    return buffer.getvalue()
