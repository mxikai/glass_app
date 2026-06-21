from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from utils.db import Base


class FundBucket(Base):
    __tablename__ = "FundBucket"

    bucket_id = Column("BucketID", Integer, primary_key=True, autoincrement=True)
    plan_id = Column("PlanID", Integer, ForeignKey("BudgetPlan.PlanID"), nullable=False)
    bucket_name = Column("BucketName", String(120), nullable=False)
    planned_amount = Column("PlannedAmount", Numeric(12, 2), nullable=False)
    description = Column("Description", String(255))

    budget_plan = relationship("BudgetPlan", back_populates="fund_buckets")
    budget_items = relationship("BudgetItem", back_populates="fund_bucket", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "bucket_id": self.bucket_id,
            "plan_id": self.plan_id,
            "bucket_name": self.bucket_name,
            "planned_amount": float(self.planned_amount) if self.planned_amount is not None else None,
            "description": self.description,
        }
