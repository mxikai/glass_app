from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from backend.models.budget_plan_model import budget_plan_students
from backend.utils.db import Base


class Student(Base):
    __tablename__ = "students"

    student_id = Column(String(32), primary_key=True)
    name = Column(String(120), nullable=False)
    program = Column(String(120))
    year_level = Column(Integer)
    role_title = Column(String(80))
    can_approve = Column(Boolean, default=False)
    status = Column(String(20), default="Active")

    budget_plans = relationship(
        "BudgetPlan",
        secondary=budget_plan_students,
        back_populates="students",
    )
    payment_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.student_id",
        back_populates="student",
    )
    approved_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.approver_id",
        back_populates="approver",
    )

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "name": self.name,
            "program": self.program,
            "year_level": self.year_level,
            "role_title": self.role_title,
            "can_approve": self.can_approve,
            "status": self.status,
            "plan_ids": [plan.plan_id for plan in self.budget_plans],
        }
