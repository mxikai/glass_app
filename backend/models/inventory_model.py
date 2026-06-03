from __future__ import annotations

from datetime import date

from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from backend.utils.db import Base


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    inventory_item_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(Integer, ForeignKey("transactions.transaction_id"), nullable=False)
    item_name = Column(String(120), nullable=False)
    quantity = Column(Integer, default=1)
    item_condition = Column(String(50))
    status = Column(String(20), default="Active")
    date_recorded = Column(Date, default=date.today)

    transaction = relationship("Transaction", back_populates="inventory_items")

    def to_dict(self) -> dict:
        return {
            "inventory_item_id": self.inventory_item_id,
            "transaction_id": self.transaction_id,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "item_condition": self.item_condition,
            "status": self.status,
            "date_recorded": self.date_recorded.isoformat() if self.date_recorded else None,
        }
