from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from utils.db import Base


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("budget_plans.plan_id"), nullable=False)
    student_id = Column(String(32), ForeignKey("students.student_id"))
    approver_id = Column(String(32), ForeignKey("students.student_id"))
    budget_item_id = Column(Integer, ForeignKey("budget_items.budget_item_id"))
    amount = Column(Numeric(12, 2), nullable=False)
    transaction_type = Column(String(20), nullable=False)
    transaction_status = Column(String(20), default="Active")
    approval_status = Column(String(20), default="Pending")
    transaction_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    receipt_path = Column(String(255))
    current_hash = Column(String(64))
    previous_hash = Column(String(64))

    budget_plan = relationship("BudgetPlan", back_populates="transactions")
    student = relationship("Student", foreign_keys=[student_id], back_populates="payment_transactions")
    approver = relationship("Student", foreign_keys=[approver_id], back_populates="approved_transactions")
    budget_item = relationship("BudgetItem", back_populates="transactions")
    inventory_items = relationship("InventoryItem", back_populates="transaction", cascade="all, delete-orphan")

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
            "current_hash": self.current_hash,
            "previous_hash": self.previous_hash,
        }
