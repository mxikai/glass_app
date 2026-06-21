from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from utils.db import Base


class Transaction(Base):
    __tablename__ = "TransactionRecord"

    transaction_id = Column("TransactionID", Integer, primary_key=True, autoincrement=True)
    plan_id = Column("PlanID", Integer, ForeignKey("BudgetPlan.PlanID"), nullable=False)
    student_id = Column("StudentID", String(32), ForeignKey("Student.StudentID"))
    approver_id = Column("ApprovedByStudentID", String(32), ForeignKey("Student.StudentID"))
    budget_item_id = Column("BudgetItemID", Integer, ForeignKey("BudgetItem.BudgetItemID"))
    amount = Column("Amount", Numeric(12, 2), nullable=False)
    transaction_type = Column("TransactionType", String(20), nullable=False)
    transaction_status = Column("TransactionStatus", String(20), default="Active")
    approval_status = Column("ApprovalStatus", String(20), default="Pending")
    transaction_date = Column("TransactionDate", DateTime, default=datetime.utcnow)
    notes = Column("Notes", Text)
    receipt_path = Column("ReceiptPath", String(255))
    amount_override_reason = Column("AmountOverrideReason", Text)
    current_hash = Column("CurrentHash", String(64))
    previous_hash = Column("PreviousHash", String(64))

    budget_plan = relationship("BudgetPlan", back_populates="transactions")
    student = relationship("Student", foreign_keys=[student_id], back_populates="payment_transactions")
    approver = relationship("Student", foreign_keys=[approver_id], back_populates="approved_transactions")
    budget_item = relationship("BudgetItem", back_populates="transactions")
    inventory_items = relationship("InventoryItem", back_populates="transaction", cascade="all, delete-orphan")
    expense_line_items = relationship(
        "ExpenseLineItem",
        back_populates="transaction",
        cascade="all, delete-orphan",
        order_by="ExpenseLineItem.line_item_id",
    )

    @property
    def computed_line_total(self) -> Decimal:
        return sum(
            (line_item.line_total for line_item in self.expense_line_items),
            Decimal("0"),
        )

    @property
    def amount_delta(self) -> Decimal:
        if self.transaction_type != "EXPENSE":
            return Decimal("0")
        return Decimal(str(self.amount or 0)) - self.computed_line_total

    def to_dict(self) -> dict:
        return {
            "transaction_id": self.transaction_id,
            "plan_id": self.plan_id,
            "student_id": self.student_id,
            "approver_id": self.approver_id,
            "budget_item_id": self.budget_item_id,
            "amount": float(self.amount) if self.amount is not None else None,
            "transaction_type": self.transaction_type,
            "transaction_status": self.transaction_status,
            "approval_status": self.approval_status,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "notes": self.notes,
            "receipt_path": self.receipt_path,
            "amount_override_reason": self.amount_override_reason,
            "current_hash": self.current_hash,
            "previous_hash": self.previous_hash,
            "line_items": [line_item.to_dict() for line_item in self.expense_line_items],
            "computed_line_total": float(self.computed_line_total),
            "amount_delta": float(self.amount_delta),
        }
