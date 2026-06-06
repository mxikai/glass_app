import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.inventory_service import (
    list_inventory_items, create_inventory_item, delete_inventory_item
)
from backend.services.transaction_service import list_transactions
# -------------------------

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, 
    QTableWidgetItem, QHeaderView, QFrame, QMessageBox, QPushButton,
    QFormLayout, QLineEdit, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt

class InventoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        self.inventory_data = []
        self.transactions_data = []
        
        self.setup_ui()
        self.load_data()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(24)

        # Left Table
        left_col = QVBoxLayout()
        title = QLabel("Organization Inventory")
        title.setObjectName("pageTitle")
        left_col.addWidget(title)

        self.table = QTableWidget()
        self.table.setObjectName("modernTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Expense Txn", "Item Name", "Qty", "Condition", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        left_col.addWidget(self.table)
        
        # Right Form Panel
        right_panel = QFrame()
        right_panel.setObjectName("profilePanel")
        right_panel.setFixedWidth(350)
        panel_layout = QVBoxLayout(right_panel)
        
        form_layout = QFormLayout()
        
        self.tx_combo = QComboBox()
        self.item_name = QLineEdit()
        self.quantity = QSpinBox()
        self.condition = QComboBox()
        self.condition.addItems(["New", "Good", "Fair", "Damaged"])
        self.status = QComboBox()
        self.status.addItems(["Available", "In Use", "Lost", "Disposed"])
        
        # --- CRITICAL: Styling applied to all inputs ---
        for widget in [self.tx_combo, self.item_name, self.quantity, self.condition, self.status]:
            widget.setObjectName("formInput")
        
        form_layout.addRow("Expense Txn", self.tx_combo)
        form_layout.addRow("Item Name", self.item_name)
        form_layout.addRow("Quantity", self.quantity)
        form_layout.addRow("Condition", self.condition)
        form_layout.addRow("Status", self.status)
        
        panel_layout.addLayout(form_layout)
        
        self.btn_save = QPushButton("Save Inventory Item")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self.save_item)
        panel_layout.addWidget(self.btn_save)
        
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self.delete_item)
        panel_layout.addWidget(self.btn_delete)
        
        panel_layout.addStretch()
        main_layout.addLayout(left_col, stretch=1)
        main_layout.addWidget(right_panel)

    def load_data(self):
        try:
            self.inventory_data = list_inventory_items()
            self.transactions_data = [t for t in list_transactions() if t.get("transaction_type") == "EXPENSE"]
            
            self.tx_combo.clear()
            for tx in self.transactions_data:
                self.tx_combo.addItem(f"Txn #{tx['transaction_id']} (₱{tx['amount']})", tx['transaction_id'])
            
            self.table.setRowCount(0)
            for row_idx, item in enumerate(self.inventory_data):
                self.table.insertRow(row_idx)
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(item.get("inventory_item_id"))))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(item.get("transaction_id"))))
                self.table.setItem(row_idx, 2, QTableWidgetItem(item.get("item_name")))
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(item.get("quantity"))))
                self.table.setItem(row_idx, 4, QTableWidgetItem(item.get("item_condition")))
                self.table.setItem(row_idx, 5, QTableWidgetItem(item.get("status")))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load inventory: {e}")

    def save_item(self):
        data = {
            "transaction_id": self.tx_combo.currentData(),
            "item_name": self.item_name.text(),
            "quantity": self.quantity.value(),
            "item_condition": self.condition.currentText(),
            "status": self.status.currentText(),
            "date_recorded": QDate.currentDate().toString(Qt.DateFormat.ISODate)
        }
        try:
            create_inventory_item(data)
            self.load_data()
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))