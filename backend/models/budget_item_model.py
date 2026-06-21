from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from utils.db import Base


class BudgetItem(Base):
    __tablename__ = "BudgetItem"

    budget_item_id = Column("BudgetItemID", Integer, primary_key=True, autoincrement=True)
    bucket_id = Column("BucketID", Integer, ForeignKey("FundBucket.BucketID"), nullable=False)
    item_name = Column("ItemName", String(120), nullable=False)
    item_type = Column("ItemType", String(50))
    planned_amount = Column("PlannedAmount", Numeric(12, 2), nullable=False)
    description = Column("Description", String(255))

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
