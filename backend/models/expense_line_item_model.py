from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from utils.db import Base


class ExpenseLineItem(Base):
    __tablename__ = "expense_line_items"

    line_item_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.transaction_id"), nullable=False)
    item_name = Column(String(120), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_cost = Column(Numeric(12, 2), nullable=False)

    transaction = relationship("Transaction", back_populates="expense_line_items")
    inventory_items = relationship("InventoryItem", back_populates="expense_line_item")

    @property
    def line_total(self) -> Decimal:
        return Decimal(str(self.quantity or 0)) * Decimal(str(self.unit_cost or 0))

    def to_dict(self) -> dict:
        return {
            "line_item_id": self.line_item_id,
            "transaction_id": self.transaction_id,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "unit_cost": float(self.unit_cost) if self.unit_cost is not None else None,
            "line_total": float(self.line_total),
        }
