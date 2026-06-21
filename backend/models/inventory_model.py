from __future__ import annotations

from datetime import date

from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from utils.db import Base


class InventoryItem(Base):
    __tablename__ = "InventoryItem"

    inventory_item_id = Column("InventoryItemID", Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(
        "PurchaseTransactionID",
        Integer,
        ForeignKey("TransactionRecord.TransactionID"),
    )
    expense_line_item_id = Column(
        "ExpenseLineItemID",
        Integer,
        ForeignKey("ExpenseLineItem.LineItemID"),
    )
    item_name = Column("ItemName", String(120), nullable=False)
    quantity = Column("Quantity", Integer, default=1)
    unit_cost = Column("UnitCost", Numeric(12, 2))
    item_condition = Column("ItemCondition", String(50))
    source_type = Column("SourceType", String(20), default="Purchase")
    source_note = Column("SourceNote", Text)
    status = Column("Status", String(20), default="Active")
    date_recorded = Column("DateRecorded", Date, default=date.today)

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
