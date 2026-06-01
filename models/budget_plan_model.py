from __future__ import annotations

from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Table
from sqlalchemy.orm import relationship

from utils.db import Base

budget_plan_students = Table(
    "budget_plan_students",
    Base.metadata,
    Column("plan_id", ForeignKey("budget_plans.plan_id"), primary_key=True),
    Column("student_id", ForeignKey("students.student_id"), primary_key=True),
)


class BudgetPlan(Base):
    __tablename__ = "budget_plans"

    plan_id = Column(Integer, primary_key=True, autoincrement=True)
    academic_year = Column(String(20), nullable=False)
    semester = Column(String(20), nullable=False)
    total_planned_budget = Column(Numeric(12, 2), nullable=False)
    member_count = Column(Integer, nullable=False)
    semestral_fee_amount = Column(Numeric(12, 2), nullable=False)
    approval_status = Column(String(20), default="Pending")
    approved_date = Column(Date)
    status = Column(String(20), default="Active")

    students = relationship("Student", secondary=budget_plan_students, back_populates="budget_plans")
    fund_buckets = relationship("FundBucket", back_populates="budget_plan", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="budget_plan", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "academic_year": self.academic_year,
            "semester": self.semester,
            "total_planned_budget": float(self.total_planned_budget)
            if self.total_planned_budget is not None
            else None,
            "member_count": self.member_count,
            "semestral_fee_amount": float(self.semestral_fee_amount)
            if self.semestral_fee_amount is not None
            else None,
            "approval_status": self.approval_status,
            "approved_date": self.approved_date.isoformat() if self.approved_date else None,
            "status": self.status,
            "student_ids": [student.student_id for student in self.students],
        }
