from __future__ import annotations

from datetime import date

from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from utils.db import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    inventory_item_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.transaction_id"))
    expense_line_item_id = Column(Integer, ForeignKey("expense_line_items.line_item_id"))
    item_name = Column(String(120), nullable=False)
    quantity = Column(Integer, default=1)
    unit_cost = Column(Numeric(12, 2))
    item_condition = Column(String(50))
    source_type = Column(String(20), default="Purchase")
    source_note = Column(Text)
    status = Column(String(20), default="Active")
    date_recorded = Column(Date, default=date.today)

    transaction = relationship("Transaction", back_populates="inventory_items")
    expense_line_item = relationship("ExpenseLineItem", back_populates="inventory_items")

    def to_dict(self) -> dict:
        return {
            "inventory_item_id": self.inventory_item_id,
            "transaction_id": self.transaction_id,
            "expense_line_item_id": self.expense_line_item_id,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "unit_cost": float(self.unit_cost) if self.unit_cost is not None else None,
            "item_condition": self.item_condition,
            "source_type": self.source_type,
            "source_note": self.source_note,
            "status": self.status,
            "date_recorded": self.date_recorded.isoformat() if self.date_recorded else None,
        }
