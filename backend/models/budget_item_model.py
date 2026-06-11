from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from utils.db import Base


class BudgetItem(Base):
    __tablename__ = "budget_items"

    budget_item_id = Column(Integer, primary_key=True, autoincrement=True)
    bucket_id = Column(Integer, ForeignKey("fund_buckets.bucket_id"), nullable=False)
    item_name = Column(String(120), nullable=False)
    item_type = Column(String(50))
    planned_amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String(255))

    fund_bucket = relationship("FundBucket", back_populates="budget_items")
    transactions = relationship("Transaction", back_populates="budget_item")

    def to_dict(self) -> dict:
        return {
            "budget_item_id": self.budget_item_id,
            "bucket_id": self.bucket_id,
            "item_name": self.item_name,
            "item_type": self.item_type,
            "planned_amount": float(self.planned_amount) if self.planned_amount is not None else None,
            "description": self.description,
        }
