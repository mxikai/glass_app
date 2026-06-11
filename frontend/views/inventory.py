import sys
import os
from datetime import date

# --- THE MASTER BRIDGE ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.inventory_service import (
    list_inventory_items, create_inventory_item, update_inventory_item, delete_inventory_item
)
from backend.services.transaction_service import list_transactions
# -------------------------

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, 
    QComboBox, QFrame, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt

class InventoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        self.current_item_id = None
        self.inventory_data = []
        self.expense_txns = []

        self.setup_ui()
        self.load_all_data()

    def showEvent(self, event):
        """Refreshes the data every time the tab is clicked!"""
        super().showEvent(event)
        self.load_all_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(24)

        # ==========================================
        # LEFT COLUMN (Main Table)
        # ==========================================
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        
        title = QLabel("Inventory Tracker")
        title.setObjectName("pageTitle")
        
        subtitle = QLabel("Inventory items are physical assets connected to expense transactions or legacy inherited items.")
        subtitle.setStyleSheet("color: #9B9BB0; font-size: 13px; margin-bottom: 8px;")
        
        left_col.addWidget(title)
        left_col.addWidget(subtitle)

        self.table = QTableWidget()
        self.table.setObjectName("modernTable")
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Source", "Item Name", "Qty", "Cost", "Condition", "Status", "Date Recorded"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # Resize smaller columns tightly
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.on_table_select)
        
        left_col.addWidget(self.table)
        
        # ==========================================
        # RIGHT COLUMN (Form Panel)
        # ==========================================
        self.right_panel = QFrame()
        self.right_panel.setObjectName("profilePanel")
        self.right_panel.setFixedWidth(380) 
        
        panel_layout = QVBoxLayout(self.right_panel)
        panel_layout.setContentsMargins(24, 32, 24, 32)
        panel_layout.setSpacing(16)
        
        form_title = QLabel("Inventory Item")
        form_title.setObjectName("panelTitle")
        form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(form_title)
        
        # --- Form Fields ---
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        
        self.input_id = QLineEdit()
        self.input_id.setReadOnly(True)
        self.input_id.setPlaceholderText("Auto-generated")
        self.input_id.setStyleSheet("background-color: #F5F6FA; color: #9B9BB0;")
        
        # New Source logic mapped to backend updates
        self.input_source = QComboBox()
        self.input_source.addItems(["Purchase", "Legacy"])
        self.input_source.currentTextChanged.connect(self.on_source_changed)

        self.lbl_txn = QLabel("Expense Txn *")
        self.input_txn = QComboBox()
        
        self.lbl_note = QLabel("Source Note *")
        self.input_note = QLineEdit()
        self.input_note.setPlaceholderText("e.g. Handed down from 2024 admins")
        
        self.input_name = QLineEdit()
        
        self.input_qty = QSpinBox()
        self.input_qty.setRange(1, 999999)
        
        self.input_cost = QDoubleSpinBox()
        self.input_cost.setRange(0, 9999999.99)
        self.input_cost.setPrefix("₱ ")
        
        # Exact values from your PDF framework
        self.input_condition = QComboBox()
        self.input_condition.addItems(["New", "Good", "Fair", "Damaged"])
        
        self.input_status = QComboBox()
        self.input_status.addItems(["Available", "In Use", "Lost", "Disposed", "Active"])
        
        self.input_date = QLineEdit()
        self.input_date.setPlaceholderText("YYYY-MM-DD")
        self.input_date.setText(str(date.today()))

        # Apply CSS styling
        for inp in [self.input_id, self.input_source, self.input_txn, self.input_note, 
                    self.input_name, self.input_qty, self.input_cost, self.input_condition, 
                    self.input_status, self.input_date]:
            inp.setObjectName("formInput")

        form_layout.addRow("Inventory ID", self.input_id)
        form_layout.addRow("Source Type", self.input_source)
        form_layout.addRow(self.lbl_txn, self.input_txn)
        form_layout.addRow(self.lbl_note, self.input_note)
        form_layout.addRow("Item Name *", self.input_name)
        form_layout.addRow("Quantity", self.input_qty)
        form_layout.addRow("Unit Cost", self.input_cost)
        form_layout.addRow("Condition", self.input_condition)
        form_layout.addRow("Status", self.input_status)
        form_layout.addRow("Date Recorded", self.input_date)
        
        panel_layout.addLayout(form_layout)
        panel_layout.addStretch()
        
        # --- Buttons ---
        self.btn_save = QPushButton("Save Inventory Item")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self.save_item)
        
        self.btn_clear = QPushButton("New")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self.clear_form)
        
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self.delete_item)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_delete)

        panel_layout.addWidget(self.btn_save)
        panel_layout.addLayout(btn_row)

        main_layout.addLayout(left_col, stretch=1)
        main_layout.addWidget(self.right_panel)

        self.on_source_changed("Purchase")

    def on_source_changed(self, source_type):
        """Morphs the form depending on Purchase vs Legacy."""
        is_purchase = (source_type == "Purchase")
        
        self.lbl_txn.setVisible(is_purchase)
        self.input_txn.setVisible(is_purchase)
        
        self.lbl_note.setVisible(not is_purchase)
        self.input_note.setVisible(not is_purchase)

    # --- Data Logic ---
    def load_all_data(self):
        try:
            self.inventory_data = list_inventory_items()
            all_transactions = list_transactions()
            
            # Inventory items can ONLY be tied to Expenses
            self.expense_txns = [t for t in all_transactions if t.get("transaction_type") == "EXPENSE"]
            
            self.populate_dropdowns()
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "Data Error", f"Could not load data: {e}")

    def populate_dropdowns(self):
        curr_txn = self.input_txn.currentData()
        
        self.input_txn.clear()
        for tx in self.expense_txns:
            if isinstance(tx, dict):
                label = f"Txn #{tx.get('transaction_id')} - ₱{float(tx.get('amount') or 0):,.2f}"
                self.input_txn.addItem(label, tx.get("transaction_id"))
                
        # Restore selection if it existed
        if curr_txn:
            idx = self.input_txn.findData(curr_txn)
            if idx >= 0:
                self.input_txn.setCurrentIndex(idx)

    def refresh_table(self):
        self.table.setRowCount(0) 
        for row_idx, item in enumerate(self.inventory_data):
            self.table.insertRow(row_idx)
            
            s_type = str(item.get("source_type", "Purchase"))
            if s_type == "Purchase":
                source_display = f"Txn #{item.get('transaction_id', '')}"
            else:
                source_display = "Legacy"

            self.table.setItem(row_idx, 0, QTableWidgetItem(str(item.get("inventory_item_id", ""))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(source_display))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(item.get("item_name", ""))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(item.get("quantity", 1))))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"₱{float(item.get('unit_cost') or 0):,.2f}"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(item.get("item_condition", ""))))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(item.get("status", "Active"))))
            
            raw_date = str(item.get("date_recorded", ""))
            clean_date = raw_date[:10] if raw_date else "Unknown"
            self.table.setItem(row_idx, 7, QTableWidgetItem(clean_date))

    # --- Interaction Logic ---
    def on_table_select(self):
        rows = self.table.selectedItems()
        if not rows: return
        
        self.current_item_id = int(self.table.item(rows[0].row(), 0).text())
        
        target_item = None
        for item in self.inventory_data:
            if isinstance(item, dict) and str(item.get("inventory_item_id")) == str(self.current_item_id):
                target_item = item
                break
                
        if target_item:
            self.input_id.setText(str(target_item.get("inventory_item_id", "")))
            self.input_source.setCurrentText(target_item.get("source_type", "Purchase"))
            
            idx_txn = self.input_txn.findData(target_item.get("transaction_id"))
            if idx_txn >= 0: 
                self.input_txn.setCurrentIndex(idx_txn)
                
            self.input_note.setText(target_item.get("source_note", ""))
            self.input_name.setText(target_item.get("item_name", ""))
            self.input_qty.setValue(int(target_item.get("quantity") or 1))
            self.input_cost.setValue(float(target_item.get("unit_cost") or 0))
            self.input_condition.setCurrentText(target_item.get("item_condition", "New"))
            self.input_status.setCurrentText(target_item.get("status", "Available"))
            
            raw_date = str(target_item.get("date_recorded", ""))
            self.input_date.setText(raw_date[:10] if raw_date else str(date.today()))

    def clear_form(self):
        self.current_item_id = None
        self.input_id.clear()
        self.input_source.setCurrentIndex(0)
        self.input_txn.setCurrentIndex(-1)
        self.input_note.clear()
        self.input_name.clear()
        self.input_qty.setValue(1)
        self.input_cost.setValue(0.0)
        self.input_condition.setCurrentIndex(0)
        self.input_status.setCurrentIndex(0)
        self.input_date.setText(str(date.today()))
        self.table.clearSelection()

    def save_item(self):
        source_type = self.input_source.currentText()
        txn_id = self.input_txn.currentData()
        name = self.input_name.text().strip()
        note = self.input_note.text().strip()
        
        # Validations enforcing the backend logic
        if source_type == "Purchase" and not txn_id:
            QMessageBox.warning(self, "Validation Error", "You must select a source Expense Transaction.")
            return
        if source_type == "Legacy" and not note:
            QMessageBox.warning(self, "Validation Error", "Source Note is required for Legacy items.")
            return
        if not name:
            QMessageBox.warning(self, "Validation Error", "Item Name is required.")
            return
            
        data = {
            "source_type": source_type,
            "transaction_id": txn_id if source_type == "Purchase" else None,
            "source_note": note if source_type == "Legacy" else "",
            "item_name": name,
            "quantity": self.input_qty.value(),
            "unit_cost": self.input_cost.value(),
            "item_condition": self.input_condition.currentText(),
            "status": self.input_status.currentText(),
            "date_recorded": self.input_date.text().strip()
        }
        
        try:
            if self.current_item_id:
                update_inventory_item(self.current_item_id, data)
            else:
                create_inventory_item(data)
                
            self.load_all_data()
            self.clear_form()
            QMessageBox.information(self, "Success", "Inventory item saved successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def delete_item(self):
        if not self.current_item_id:
            QMessageBox.warning(self, "Selection Error", "Please select an item to delete.")
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     "Are you sure you want to delete this inventory record?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_inventory_item(self.current_item_id)
                self.load_all_data()
                self.clear_form()
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", str(e))