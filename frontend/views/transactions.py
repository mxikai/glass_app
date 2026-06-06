import sys
import os

# --- THE MASTER BRIDGE ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.transaction_service import list_transactions, create_transaction, update_transaction, delete_transaction
from backend.services.budget_service import list_budget_plans, list_budget_items
from backend.services.student_service import list_students
from backend.services.inventory_service import create_inventory_item
# -------------------------

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, 
    QComboBox, QFrame, QDoubleSpinBox, QGroupBox, QSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt

class TransactionsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        self.current_transaction_id = None 
        self.transactions_data = []
        self.plans_data = []
        self.students_data = []
        self.items_data = []

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
        
        title = QLabel("Transaction Ledger")
        title.setObjectName("pageTitle")
        left_col.addWidget(title)

        self.table = QTableWidget()
        self.table.setObjectName("modernTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date", "Type", "Amount", "Status", "Approval"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumWidth(400) 
        self.table.itemSelectionChanged.connect(self.on_table_select)
        
        left_col.addWidget(self.table)
        
        # ==========================================
        # RIGHT COLUMN (Dynamic Form Panel WITH SCROLL)
        # ==========================================
        self.right_panel = QFrame()
        self.right_panel.setObjectName("profilePanel")
        self.right_panel.setFixedWidth(380) 
        
        panel_outer_layout = QVBoxLayout(self.right_panel)
        panel_outer_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; } QWidget#scrollContainer { background: transparent; }")
        
        scroll_container = QWidget()
        scroll_container.setObjectName("scrollContainer")
        
        panel_layout = QVBoxLayout(scroll_container)
        panel_layout.setContentsMargins(24, 24, 24, 24)
        panel_layout.setSpacing(16)
        
        form_title = QLabel("Transaction Details")
        form_title.setObjectName("panelTitle")
        form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(form_title)
        
        # --- Core Form Fields ---
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        
        self.input_plan = QComboBox()
        self.input_type = QComboBox()
        self.input_type.addItems(["PAYMENT", "EXPENSE"])
        self.input_type.currentTextChanged.connect(self.on_type_changed)
        
        self.input_amount = QDoubleSpinBox()
        self.input_amount.setRange(0, 9999999)
        self.input_amount.setPrefix("₱ ")
        
        self.lbl_student = QLabel("Student (Payer)")
        self.input_student = QComboBox()
        
        self.lbl_item = QLabel("Budget Item")
        self.input_item = QComboBox()
        
        self.lbl_approver = QLabel("Approved By")
        self.input_approver = QComboBox()
        
        self.lbl_receipt = QLabel("Receipt Path")
        self.input_receipt = QLineEdit()
        self.input_receipt.setPlaceholderText("File path...")

        self.input_status = QComboBox()
        self.input_status.addItems(["Active", "Void"])
        
        self.input_approval = QComboBox()
        self.input_approval.addItems(["Pending", "Approved", "Rejected"])

        self.input_notes = QLineEdit()
        self.input_notes.setPlaceholderText("Optional notes...")

        form_layout.addRow("Budget Plan *", self.input_plan)
        form_layout.addRow("Type *", self.input_type)
        form_layout.addRow("Amount *", self.input_amount)
        form_layout.addRow(self.lbl_student, self.input_student)
        form_layout.addRow(self.lbl_item, self.input_item)
        form_layout.addRow(self.lbl_approver, self.input_approver)
        form_layout.addRow("Status", self.input_status)
        form_layout.addRow("Approval", self.input_approval)
        form_layout.addRow(self.lbl_receipt, self.input_receipt)
        form_layout.addRow("Notes", self.input_notes)
        
        panel_layout.addLayout(form_layout)

        # --- INVENTORY SECTION (Only for Expenses) ---
        self.group_inventory = QGroupBox("Inventory Details (Optional)")
        self.group_inventory.setStyleSheet("QGroupBox { font-weight: bold; color: #6C5CE7; padding-top: 15px; margin-top: 10px; }")
        inv_layout = QFormLayout()
        inv_layout.setVerticalSpacing(10)

        self.inv_name = QLineEdit()
        self.inv_name.setPlaceholderText("e.g. Printer Ink")
        
        self.inv_qty = QSpinBox()
        self.inv_qty.setRange(1, 999)
        
        self.inv_condition = QComboBox()
        self.inv_condition.addItems(["New", "Good", "Fair", "Poor"])
        
        self.inv_status = QComboBox()
        self.inv_status.addItems(["Active", "In Use", "Stored", "Lost/Damaged", "Disposed"])

        inv_layout.addRow("Item Name", self.inv_name)
        inv_layout.addRow("Quantity", self.inv_qty)
        inv_layout.addRow("Condition", self.inv_condition)
        inv_layout.addRow("Status", self.inv_status)
        
        self.group_inventory.setLayout(inv_layout)
        panel_layout.addWidget(self.group_inventory)

        panel_layout.addStretch()
        
        # --- Buttons ---
        self.btn_save = QPushButton("Save Transaction")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self.save_transaction)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self.clear_form)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self.delete_transaction)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_delete)

        panel_layout.addWidget(self.btn_save)
        panel_layout.addLayout(btn_row)

        scroll_area.setWidget(scroll_container)
        panel_outer_layout.addWidget(scroll_area)

        main_layout.addLayout(left_col, stretch=1)
        main_layout.addWidget(self.right_panel)

        for inp in [self.input_plan, self.input_type, self.input_amount, self.input_student, 
                    self.input_item, self.input_approver, self.input_status, self.input_approval, 
                    self.input_receipt, self.input_notes, self.inv_name, self.inv_qty, 
                    self.inv_condition, self.inv_status]:
            inp.setObjectName("formInput")

        self.on_type_changed("PAYMENT")

    def on_type_changed(self, tx_type):
        is_payment = (tx_type == "PAYMENT")
        
        self.lbl_student.setVisible(is_payment)
        self.input_student.setVisible(is_payment)
        
        self.lbl_item.setVisible(not is_payment)
        self.input_item.setVisible(not is_payment)
        
        # --- THE FIX: ALWAYS VISIBLE NOW ---
        self.lbl_approver.setVisible(True)
        self.input_approver.setVisible(True)
        # -----------------------------------

        self.lbl_receipt.setVisible(not is_payment)
        self.input_receipt.setVisible(not is_payment)
        
        self.group_inventory.setVisible(not is_payment)

    def load_all_data(self):
        try:
            self.transactions_data = list_transactions()
            self.plans_data = list_budget_plans()
            self.students_data = list_students()
            self.items_data = list_budget_items()
            
            self.populate_dropdowns()
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "Data Error", f"Could not load data: {e}")

    def populate_dropdowns(self):
        self.input_plan.clear()
        for p in self.plans_data:
            if isinstance(p, dict):
                self.input_plan.addItem(f"Plan {p.get('plan_id')} ({p.get('academic_year')})", p.get("plan_id"))

        self.input_student.clear()
        self.input_approver.clear()
        self.input_approver.addItem("-- Pending Approver --", None) 
        
        for s in self.students_data:
            if isinstance(s, dict):
                label = f"{s.get('name')} ({s.get('student_id')})"
                self.input_student.addItem(label, s.get("student_id"))
                
                raw_val = s.get("can_approve")
                is_approver = False
                
                if isinstance(raw_val, bool):
                    is_approver = raw_val
                elif isinstance(raw_val, int):
                    is_approver = (raw_val == 1)
                elif isinstance(raw_val, str):
                    is_approver = raw_val.strip().lower() in ['true', '1', 'yes', 't', 'y']

                if is_approver:
                    self.input_approver.addItem(label, s.get("student_id"))

        self.input_item.clear()
        for i in self.items_data:
            if isinstance(i, dict):
                self.input_item.addItem(f"{i.get('item_name')}", i.get("budget_item_id"))

    def refresh_table(self):
        self.table.setRowCount(0) 
        for row_idx, t in enumerate(self.transactions_data):
            self.table.insertRow(row_idx)
            
            raw_date = str(t.get("transaction_date", ""))
            clean_date = raw_date[:10] if raw_date else "Unknown"
            
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(t.get("transaction_id", ""))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(clean_date))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(t.get("transaction_type", ""))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"₱{float(t.get('amount') or 0):,.2f}"))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(t.get("transaction_status", "Active"))))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(t.get("approval_status", "Pending"))))

    def on_table_select(self):
        rows = self.table.selectedItems()
        if not rows: return
        
        self.current_transaction_id = int(self.table.item(rows[0].row(), 0).text())
        
        tx = None
        for t in self.transactions_data:
            if isinstance(t, dict) and str(t.get("transaction_id")) == str(self.current_transaction_id):
                tx = t
                break
                
        if tx:
            idx_plan = self.input_plan.findData(tx.get("plan_id"))
            if idx_plan >= 0: self.input_plan.setCurrentIndex(idx_plan)
            
            self.input_type.setCurrentText(tx.get("transaction_type", "PAYMENT"))
            self.input_amount.setValue(float(tx.get("amount") or 0))
            
            if tx.get("student_id"):
                idx_stu = self.input_student.findData(tx.get("student_id"))
                if idx_stu >= 0: self.input_student.setCurrentIndex(idx_stu)
                
            if tx.get("budget_item_id"):
                idx_item = self.input_item.findData(tx.get("budget_item_id"))
                if idx_item >= 0: self.input_item.setCurrentIndex(idx_item)
                
            if tx.get("approver_id"):
                idx_app = self.input_approver.findData(tx.get("approver_id"))
                if idx_app >= 0: self.input_approver.setCurrentIndex(idx_app)

            self.input_status.setCurrentText(tx.get("transaction_status", "Active"))
            self.input_approval.setCurrentText(tx.get("approval_status", "Pending"))
            self.input_receipt.setText(tx.get("receipt_path") or "")
            self.input_notes.setText(tx.get("notes") or "")
            
            self.inv_name.clear()
            self.inv_qty.setValue(1)
            self.inv_condition.setCurrentIndex(0)
            self.inv_status.setCurrentIndex(0)

    def clear_form(self):
        self.current_transaction_id = None
        self.input_amount.setValue(0)
        self.input_receipt.clear()
        self.input_notes.clear()
        self.input_status.setCurrentIndex(0)
        self.input_approval.setCurrentIndex(0)
        self.input_approver.setCurrentIndex(0)
        
        self.inv_name.clear()
        self.inv_qty.setValue(1)
        self.inv_condition.setCurrentIndex(0)
        self.inv_status.setCurrentIndex(0)
        
        self.table.clearSelection()

    def save_transaction(self):
        tx_type = self.input_type.currentText()
        plan_id = self.input_plan.currentData()
        
        if not plan_id:
            QMessageBox.warning(self, "Validation Error", "You must select a Budget Plan!")
            return
            
        # --- THE FIX: Approver is explicitly bundled for ALL transaction types! ---
        data = {
            "plan_id": plan_id,
            "transaction_type": tx_type,
            "amount": self.input_amount.value(),
            "transaction_status": self.input_status.currentText(),
            "approval_status": self.input_approval.currentText(),
            "approver_id": self.input_approver.currentData(), 
            "notes": self.input_notes.text().strip()
        }
        
        if tx_type == "PAYMENT":
            data["student_id"] = self.input_student.currentData()
        else: 
            data["budget_item_id"] = self.input_item.currentData()
            data["receipt_path"] = self.input_receipt.text().strip()
            
        # Validate that an approver exists if the status is "Approved"
        if data["approval_status"] == "Approved" and not data.get("approver_id"):
            QMessageBox.warning(self, "Validation Error", "You must select an Officer to approve this transaction!")
            return
        # -------------------------------------------------------------------------
        
        try:
            if self.current_transaction_id:
                new_tx = update_transaction(self.current_transaction_id, data)
                active_tx_id = self.current_transaction_id
            else:
                new_tx = create_transaction(data)
                active_tx_id = new_tx.get("transaction_id")
                
            if tx_type == "EXPENSE" and self.inv_name.text().strip():
                inv_data = {
                    "item_name": self.inv_name.text().strip(),
                    "quantity": self.inv_qty.value(),
                    "item_condition": self.inv_condition.currentText(), 
                    "status": self.inv_status.currentText(),
                    "transaction_id": active_tx_id
                }
                create_inventory_item(inv_data)
                
            self.load_all_data()
            self.clear_form()
            QMessageBox.information(self, "Success", "Transaction (and Inventory if applicable) saved successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def delete_transaction(self):
        if not self.current_transaction_id:
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     "Are you sure you want to delete this transaction?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_transaction(self.current_transaction_id)
                self.load_all_data()
                self.clear_form()
            except Exception as e:
                QMessageBox.critical(self, "Delete Blocked", str(e))