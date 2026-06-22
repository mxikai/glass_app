import sys
import os

# --- THE MASTER BRIDGE ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.transaction_service import list_transactions, create_transaction, update_transaction, delete_transaction
from backend.services.budget_service import list_budget_plans, list_budget_items, list_fund_buckets
from backend.services.student_service import list_students
# -------------------------

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, 
    QComboBox, QFrame, QDoubleSpinBox, QGroupBox, QSpinBox, 
    QScrollArea, QTabWidget, QStackedWidget, QDateTimeEdit, QDialog, QInputDialog,
    QCompleter
)
from PyQt6.QtCore import Qt, QDateTime, QStringListModel

class AddLineItemDialog(QDialog):
    """A clean mini-dialog to add individual line items to an expense."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Line Item")
        self.setFixedSize(320, 180)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        
        layout = QFormLayout(self)
        
        self.input_name = QLineEdit()
        self.input_name.setObjectName("formInput")
        self.input_name.setPlaceholderText("e.g., Bond Paper (Ream)")
        
        self.input_qty = QSpinBox()
        self.input_qty.setObjectName("formInput")
        self.input_qty.setRange(1, 99999)
        
        self.input_cost = QDoubleSpinBox()
        self.input_cost.setObjectName("formInput")
        self.input_cost.setRange(0.01, 999999.99)
        self.input_cost.setPrefix("₱ ")
        
        layout.addRow("Item Name:", self.input_name)
        layout.addRow("Quantity:", self.input_qty)
        layout.addRow("Unit Cost:", self.input_cost)
        
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Add")
        btn_save.setObjectName("primaryBtn")
        btn_save.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addRow(btn_layout)

    def get_data(self):
        return {
            "item_name": self.input_name.text().strip(),
            "quantity": self.input_qty.value(),
            "unit_cost": self.input_cost.value()
        }


class TransactionsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        self.current_payment_id = None
        self.current_expense_id = None
        
        self.transactions_data = []
        self.plans_data = []
        self.buckets_data = []
        self.items_data = []
        self.students_data = []
        
        self.current_line_items = []
        self.student_mapping = {}

        # --- PAGINATION TRACKERS ---
        self.pay_page = 1
        self.exp_page = 1
        self.items_per_page = 50

        self.setup_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_all_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(24)

        # ==========================================
        # LEFT COLUMN (Tabs & Tables)
        # ==========================================
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        
        header_layout = QHBoxLayout()
        title = QLabel("Transaction Ledger")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        lbl_filter = QLabel("Filter by Plan:")
        lbl_filter.setStyleSheet("font-weight: 600; color: #9B9BB0; font-size: 13px; font-family: 'Segoe UI';")
        self.filter_plan_cb = QComboBox()
        self.filter_plan_cb.setObjectName("formInput")
        self.filter_plan_cb.setFixedWidth(220)
        self.filter_plan_cb.currentIndexChanged.connect(self.on_filter_changed)
        
        header_layout.addWidget(lbl_filter)
        header_layout.addWidget(self.filter_plan_cb)
        
        left_col.addLayout(header_layout)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("modernTabs")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # --- TAB 1: PAYMENTS (With Pagination) ---
        self.tab_pay = QWidget()
        pay_layout = QVBoxLayout(self.tab_pay)
        pay_layout.setContentsMargins(0, 10, 0, 0)
        
        self.table_payments = self._create_table(["ID", "Date", "Student", "Amount", "Approval", "Status"])
        self.table_payments.itemSelectionChanged.connect(self.on_payment_select)
        pay_layout.addWidget(self.table_payments)
        
        pay_ctrl = QHBoxLayout()
        self.pay_prev = QPushButton("◄ Prev")
        self.pay_prev.setObjectName("secondaryBtn")
        self.pay_prev.setFixedWidth(80)
        self.pay_prev.clicked.connect(self.pay_prev_page)
        
        self.pay_lbl = QLabel("Page 1 of 1")
        self.pay_lbl.setStyleSheet("color: #9B9BB0; font-weight: bold;")
        
        self.pay_next = QPushButton("Next ►")
        self.pay_next.setObjectName("secondaryBtn")
        self.pay_next.setFixedWidth(80)
        self.pay_next.clicked.connect(self.pay_next_page)
        
        pay_ctrl.addWidget(self.pay_prev)
        pay_ctrl.addStretch()
        pay_ctrl.addWidget(self.pay_lbl)
        pay_ctrl.addStretch()
        pay_ctrl.addWidget(self.pay_next)
        pay_layout.addLayout(pay_ctrl)
        
        self.tabs.addTab(self.tab_pay, "Payments")

        # --- TAB 2: EXPENSES (With Pagination) ---
        self.tab_exp = QWidget()
        exp_layout = QVBoxLayout(self.tab_exp)
        exp_layout.setContentsMargins(0, 10, 0, 0)
        
        self.table_expenses = self._create_table(["ID", "Date", "Budget Item", "Amount", "Approval", "Status"])
        self.table_expenses.itemSelectionChanged.connect(self.on_expense_select)
        exp_layout.addWidget(self.table_expenses)
        
        exp_ctrl = QHBoxLayout()
        self.exp_prev = QPushButton("◄ Prev")
        self.exp_prev.setObjectName("secondaryBtn")
        self.exp_prev.setFixedWidth(80)
        self.exp_prev.clicked.connect(self.exp_prev_page)
        
        self.exp_lbl = QLabel("Page 1 of 1")
        self.exp_lbl.setStyleSheet("color: #9B9BB0; font-weight: bold;")
        
        self.exp_next = QPushButton("Next ►")
        self.exp_next.setObjectName("secondaryBtn")
        self.exp_next.setFixedWidth(80)
        self.exp_next.clicked.connect(self.exp_next_page)
        
        exp_ctrl.addWidget(self.exp_prev)
        exp_ctrl.addStretch()
        exp_ctrl.addWidget(self.exp_lbl)
        exp_ctrl.addStretch()
        exp_ctrl.addWidget(self.exp_next)
        exp_layout.addLayout(exp_ctrl)
        
        self.tabs.addTab(self.tab_exp, "Expenses")

        left_col.addWidget(self.tabs)

        # ==========================================
        # RIGHT COLUMN (Profile Panel & Stacked Forms)
        # ==========================================
        self.right_panel = QFrame()
        self.right_panel.setObjectName("profilePanel")
        self.right_panel.setFixedWidth(400) 
        
        panel_layout = QVBoxLayout(self.right_panel)
        panel_layout.setContentsMargins(24, 32, 24, 32)
        panel_layout.setSpacing(16)
        
        self.form_title = QLabel("Payment Details")
        self.form_title.setObjectName("panelTitle")
        self.form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.form_title)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; } QWidget#scrollContainer { background: transparent; }")
        
        scroll_container = QWidget()
        scroll_container.setObjectName("scrollContainer")
        scroll_layout = QVBoxLayout(scroll_container)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        self.form_stack = QStackedWidget()
        self.setup_payment_form()
        self.setup_expense_form()
        
        scroll_layout.addWidget(self.form_stack)
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_container)
        
        panel_layout.addWidget(scroll_area)

        self.btn_save = QPushButton("Save Payment")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self.save_current_form)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self.clear_current_form)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self.delete_current_record)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_delete)

        panel_layout.addWidget(self.btn_save)
        panel_layout.addLayout(btn_row)

        main_layout.addLayout(left_col, stretch=1)
        main_layout.addWidget(self.right_panel)

    def _create_table(self, headers):
        table = QTableWidget()
        table.setObjectName("modernTable")
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setShowGrid(False) 
        table.verticalHeader().setVisible(False)
        return table

    def setup_payment_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setVerticalSpacing(12)
        
        self.pay_plan = QComboBox()
        self.pay_plan.currentIndexChanged.connect(self.filter_students)
        
        self.pay_student = QLineEdit()
        self.pay_student.setPlaceholderText("Search Name or ID...")
        self.student_completer = QCompleter()
        self.student_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.student_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.pay_student.setCompleter(self.student_completer)
        
        self.pay_amount = QDoubleSpinBox()
        self.pay_amount.setRange(0, 9999999)
        self.pay_amount.setPrefix("₱ ")
        
        self.pay_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.pay_date.setDisplayFormat("yyyy-MM-dd HH:mm")
        
        self.pay_approval = QComboBox()
        self.pay_approval.addItems(["Pending", "Approved", "Rejected"])
        self.pay_approver = QComboBox()
        self.pay_status = QComboBox()
        self.pay_status.addItems(["Active", "Void"])
        self.pay_notes = QLineEdit()

        for w in [self.pay_plan, self.pay_student, self.pay_amount, self.pay_date, 
                  self.pay_approval, self.pay_approver, self.pay_status, self.pay_notes]:
            w.setObjectName("formInput")

        layout.addRow("Budget Plan", self.pay_plan)
        layout.addRow("Search Student", self.pay_student)
        layout.addRow("Amount", self.pay_amount)
        layout.addRow("Date/Time", self.pay_date)
        layout.addRow("Approval", self.pay_approval)
        layout.addRow("Approved By", self.pay_approver)
        layout.addRow("Status", self.pay_status)
        layout.addRow("Notes", self.pay_notes)
        
        self.form_stack.addWidget(widget)

    def setup_expense_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setVerticalSpacing(12)
        
        self.exp_plan = QComboBox()
        self.exp_bucket = QComboBox()
        self.exp_item = QComboBox()
        
        self.exp_plan.currentIndexChanged.connect(self.filter_fund_buckets)
        self.exp_bucket.currentIndexChanged.connect(self.filter_budget_items)
        
        self.exp_date = QDateTimeEdit(QDateTime.currentDateTime())
        self.exp_date.setDisplayFormat("yyyy-MM-dd HH:mm")
        
        self.exp_approval = QComboBox()
        self.exp_approval.addItems(["Pending", "Approved", "Rejected"])
        self.exp_approver = QComboBox()
        self.exp_status = QComboBox()
        self.exp_status.addItems(["Active", "Void"])
        
        self.exp_receipt = QLineEdit()
        self.exp_notes = QLineEdit()

        for w in [self.exp_plan, self.exp_bucket, self.exp_item, self.exp_date, 
                  self.exp_approval, self.exp_approver, self.exp_status, self.exp_receipt, self.exp_notes]:
            w.setObjectName("formInput")

        layout.addRow("Budget Plan", self.exp_plan)
        layout.addRow("Fund Bucket", self.exp_bucket)
        layout.addRow("Budget Item", self.exp_item)
        layout.addRow("Date/Time", self.exp_date)
        layout.addRow("Approval", self.exp_approval)
        layout.addRow("Approved By", self.exp_approver)
        layout.addRow("Status", self.exp_status)
        layout.addRow("Receipt Path", self.exp_receipt)
        layout.addRow("Notes", self.exp_notes)
        
        # --- LINE ITEMS ---
        self.group_lines = QGroupBox("Receipt Line Items")
        self.group_lines.setStyleSheet("QGroupBox { font-weight: bold; color: #6C5CE7; padding-top: 15px; margin-top: 5px; border: none;}")
        lines_layout = QVBoxLayout()
        lines_layout.setContentsMargins(0, 10, 0, 0)
        
        self.table_lines = QTableWidget()
        self.table_lines.setObjectName("modernTable")
        self.table_lines.setColumnCount(4)
        self.table_lines.setHorizontalHeaderLabels(["Item", "Qty", "Cost", "Sub"])
        self.table_lines.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_lines.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_lines.setFixedHeight(130)
        self.table_lines.verticalHeader().setVisible(False)
        lines_layout.addWidget(self.table_lines)
        
        lines_btn_layout = QHBoxLayout()
        self.btn_add_line = QPushButton("Add")
        self.btn_add_line.setObjectName("secondaryBtn")
        self.btn_add_line.clicked.connect(self.add_line)
        
        self.btn_remove_line = QPushButton("Remove")
        self.btn_remove_line.setObjectName("dangerBtn")
        self.btn_remove_line.clicked.connect(self.remove_line)
        
        self.lbl_line_total = QLabel("Total: ₱ 0.00")
        self.lbl_line_total.setStyleSheet("font-weight: bold; color: #333; font-size: 13px;")
        
        lines_btn_layout.addWidget(self.btn_add_line)
        lines_btn_layout.addWidget(self.btn_remove_line)
        lines_btn_layout.addStretch()
        lines_btn_layout.addWidget(self.lbl_line_total)
        
        lines_layout.addLayout(lines_btn_layout)
        self.group_lines.setLayout(lines_layout)
        
        layout.addRow(self.group_lines)
        self.form_stack.addWidget(widget)

    # --- PAGINATION BUTTON ACTIONS ---
    def pay_prev_page(self):
        if self.pay_page > 1:
            self.pay_page -= 1
            self.refresh_payments_table()

    def pay_next_page(self):
        self.pay_page += 1
        self.refresh_payments_table()

    def exp_prev_page(self):
        if self.exp_page > 1:
            self.exp_page -= 1
            self.refresh_expenses_table()

    def exp_next_page(self):
        self.exp_page += 1
        self.refresh_expenses_table()

    def on_filter_changed(self):
        """Reset pagination when the filter changes!"""
        self.pay_page = 1
        self.exp_page = 1
        self.refresh_payments_table()
        self.refresh_expenses_table()

    # --- DATA LOADING ---
    def load_all_data(self):
        try:
            self.transactions_data = list_transactions()
            self.plans_data = list_budget_plans()
            self.buckets_data = list_fund_buckets()
            self.items_data = list_budget_items()
            self.students_data = list_students()
            
            self.populate_dropdowns()
            self.filter_students()
            self.refresh_payments_table()
            self.refresh_expenses_table()
        except Exception as e:
            QMessageBox.warning(self, "Data Error", f"Could not load data: {e}")

    def populate_dropdowns(self):
        self.filter_plan_cb.blockSignals(True)
        current_filter = self.filter_plan_cb.currentData()
        self.filter_plan_cb.clear()
        self.filter_plan_cb.addItem("All Plans", None)
        
        self.pay_plan.blockSignals(True)
        self.exp_plan.blockSignals(True)
        self.pay_plan.clear()
        self.exp_plan.clear()
        
        for p in self.plans_data:
            plan_text = f"Plan {p.get('plan_id')} ({p.get('academic_year')})"
            self.filter_plan_cb.addItem(plan_text, p.get("plan_id"))
            self.pay_plan.addItem(plan_text, p.get("plan_id"))
            self.exp_plan.addItem(plan_text, p.get("plan_id"))
            
        if current_filter:
            idx = self.filter_plan_cb.findData(current_filter)
            if idx >= 0: self.filter_plan_cb.setCurrentIndex(idx)
            
        self.filter_plan_cb.blockSignals(False)
        self.pay_plan.blockSignals(False)
        self.exp_plan.blockSignals(False)

        self.pay_approver.clear()
        self.exp_approver.clear()
        self.pay_approver.addItem("-- Pending Approver --", None)
        self.exp_approver.addItem("-- Pending Approver --", None)
        
        for s in self.students_data:
            label = f"{s.get('name')} ({s.get('student_id')})"
            if str(s.get("can_approve", "")).lower() in ['true', '1', 'yes', 't', 'y']:
                self.pay_approver.addItem(label, s.get("student_id"))
                self.exp_approver.addItem(label, s.get("student_id"))

        self.filter_fund_buckets()

    def filter_fund_buckets(self):
        self.exp_bucket.blockSignals(True)
        self.exp_bucket.clear()
        
        plan_id = self.exp_plan.currentData()
        if plan_id:
            filtered = [b for b in self.buckets_data if b.get('plan_id') == plan_id]
            for b in filtered:
                self.exp_bucket.addItem(b.get('bucket_name'), b.get('bucket_id'))
                
        self.exp_bucket.blockSignals(False)
        self.filter_budget_items()

    def filter_budget_items(self):
        self.exp_item.clear()
        
        bucket_id = self.exp_bucket.currentData()
        if not bucket_id: return
        
        filtered = [i for i in self.items_data if i.get('bucket_id') == bucket_id]
        for i in filtered:
            self.exp_item.addItem(i['item_name'], i['budget_item_id'])

    def filter_students(self):
        plan_id = self.pay_plan.currentData()
        if not plan_id: return

        paid_student_ids = set()
        for t in self.transactions_data:
            if t.get("transaction_type") == "PAYMENT" and t.get("plan_id") == plan_id:
                if t.get("transaction_status") != "Void":
                    paid_student_ids.add(t.get("student_id"))

        editing_student_id = None
        if self.current_payment_id:
            tx = next((t for t in self.transactions_data if str(t.get("transaction_id")) == str(self.current_payment_id)), None)
            if tx: editing_student_id = tx.get("student_id")

        current_text = self.pay_student.text()

        self.student_mapping = {}
        valid_strings = []

        for s in self.students_data:
            sid = s.get('student_id')
            if sid not in paid_student_ids or sid == editing_student_id:
                formatted = f"{s.get('name')} ({sid})"
                self.student_mapping[formatted] = sid
                valid_strings.append(formatted)

        model = QStringListModel()
        model.setStringList(valid_strings)
        self.student_completer.setModel(model)
        
        if current_text and current_text not in valid_strings:
            self.pay_student.clear()

    # --- TABLES & PAGINATION LOGIC ---
    def refresh_payments_table(self):
        self.table_payments.setRowCount(0)
        filter_plan_id = self.filter_plan_cb.currentData()
        
        payments = [t for t in self.transactions_data if t.get("transaction_type") == "PAYMENT"]
        
        if filter_plan_id:
            payments = [t for t in payments if t.get("plan_id") == filter_plan_id]
            
        total_items = len(payments)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        if self.pay_page > total_pages: self.pay_page = max(1, total_pages)
        
        self.pay_lbl.setText(f"Page {self.pay_page} of {total_pages}")
        self.pay_prev.setEnabled(self.pay_page > 1)
        self.pay_next.setEnabled(self.pay_page < total_pages)
        
        start_idx = (self.pay_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_data = payments[start_idx:end_idx]
            
        for row, t in enumerate(page_data):
            self.table_payments.insertRow(row)
            self.table_payments.setItem(row, 0, QTableWidgetItem(str(t.get("transaction_id", ""))))
            self.table_payments.setItem(row, 1, QTableWidgetItem(str(t.get("transaction_date", ""))[:10]))
            self.table_payments.setItem(row, 2, QTableWidgetItem(str(t.get("student_id", ""))))
            self.table_payments.setItem(row, 3, QTableWidgetItem(f"₱{float(t.get('amount') or 0):,.2f}"))
            self.table_payments.setItem(row, 4, QTableWidgetItem(str(t.get("approval_status", ""))))
            self.table_payments.setItem(row, 5, QTableWidgetItem(str(t.get("transaction_status", ""))))

    def refresh_expenses_table(self):
        self.table_expenses.setRowCount(0)
        filter_plan_id = self.filter_plan_cb.currentData()
        
        expenses = [t for t in self.transactions_data if t.get("transaction_type") == "EXPENSE"]
        
        if filter_plan_id:
            expenses = [t for t in expenses if t.get("plan_id") == filter_plan_id]
            
        total_items = len(expenses)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        if self.exp_page > total_pages: self.exp_page = max(1, total_pages)
        
        self.exp_lbl.setText(f"Page {self.exp_page} of {total_pages}")
        self.exp_prev.setEnabled(self.exp_page > 1)
        self.exp_next.setEnabled(self.exp_page < total_pages)
        
        start_idx = (self.exp_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_data = expenses[start_idx:end_idx]
            
        for row, t in enumerate(page_data):
            self.table_expenses.insertRow(row)
            item_name = next((i['item_name'] for i in self.items_data if i['budget_item_id'] == t.get("budget_item_id")), str(t.get("budget_item_id", "")))
            
            self.table_expenses.setItem(row, 0, QTableWidgetItem(str(t.get("transaction_id", ""))))
            self.table_expenses.setItem(row, 1, QTableWidgetItem(str(t.get("transaction_date", ""))[:10]))
            self.table_expenses.setItem(row, 2, QTableWidgetItem(item_name))
            self.table_expenses.setItem(row, 3, QTableWidgetItem(f"₱{float(t.get('amount') or 0):,.2f}"))
            self.table_expenses.setItem(row, 4, QTableWidgetItem(str(t.get("approval_status", ""))))
            self.table_expenses.setItem(row, 5, QTableWidgetItem(str(t.get("transaction_status", ""))))

    def refresh_lines_ui(self):
        self.table_lines.setRowCount(0)
        total = 0.0
        for row, item in enumerate(self.current_line_items):
            self.table_lines.insertRow(row)
            subtotal = item['quantity'] * item['unit_cost']
            total += subtotal
            
            self.table_lines.setItem(row, 0, QTableWidgetItem(item['item_name']))
            self.table_lines.setItem(row, 1, QTableWidgetItem(str(item['quantity'])))
            self.table_lines.setItem(row, 2, QTableWidgetItem(f"{item['unit_cost']:.2f}"))
            self.table_lines.setItem(row, 3, QTableWidgetItem(f"{subtotal:.2f}"))
            
        self.lbl_line_total.setText(f"Total: ₱ {total:,.2f}")

    def add_line(self):
        dialog = AddLineItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data["item_name"]: return
            self.current_line_items.append(data)
            self.refresh_lines_ui()

    def remove_line(self):
        rows = self.table_lines.selectedItems()
        if not rows: return
        self.current_line_items.pop(rows[0].row())
        self.refresh_lines_ui()

    # --- SELECTIONS & TABS ---
    def on_tab_changed(self, index):
        if not hasattr(self, 'form_stack'): return 
        
        self.form_stack.setCurrentIndex(index)
        self.form_title.setText("Payment Details" if index == 0 else "Expense Details")
        self.btn_save.setText("Save Payment" if index == 0 else "Save Expense")
        
        if index == 0 and not self.current_payment_id: self.clear_current_form()
        elif index == 1 and not self.current_expense_id: self.clear_current_form()

    def on_payment_select(self):
        rows = self.table_payments.selectedItems()
        if not rows: return
        
        self.current_payment_id = int(self.table_payments.item(rows[0].row(), 0).text())
        tx = next((t for t in self.transactions_data if str(t.get("transaction_id")) == str(self.current_payment_id)), None)
        if not tx: return
        
        idx_plan = self.pay_plan.findData(tx.get("plan_id"))
        if idx_plan >= 0: self.pay_plan.setCurrentIndex(idx_plan)
        
        self.filter_students()
        
        stu_id = tx.get("student_id")
        student = next((s for s in self.students_data if s.get("student_id") == stu_id), None)
        if student:
            self.pay_student.setText(f"{student.get('name')} ({stu_id})")
        else:
            self.pay_student.clear()
        
        self.pay_amount.setValue(float(tx.get("amount") or 0))
        
        if tx.get("transaction_date"):
            dt = QDateTime.fromString(tx["transaction_date"], Qt.DateFormat.ISODate)
            self.pay_date.setDateTime(dt)
            
        self.pay_approval.setCurrentText(tx.get("approval_status", "Pending"))
        self.pay_status.setCurrentText(tx.get("transaction_status", "Active"))
        self.pay_notes.setText(tx.get("notes") or "")
        
        idx_app = self.pay_approver.findData(tx.get("approver_id"))
        self.pay_approver.setCurrentIndex(idx_app if idx_app >= 0 else 0)

    def on_expense_select(self):
        rows = self.table_expenses.selectedItems()
        if not rows: return
        
        self.current_expense_id = int(self.table_expenses.item(rows[0].row(), 0).text())
        tx = next((t for t in self.transactions_data if str(t.get("transaction_id")) == str(self.current_expense_id)), None)
        if not tx: return
        
        idx_plan = self.exp_plan.findData(tx.get("plan_id"))
        if idx_plan >= 0: self.exp_plan.setCurrentIndex(idx_plan)

        if tx.get("transaction_date"):
            dt = QDateTime.fromString(tx["transaction_date"], Qt.DateFormat.ISODate)
            self.exp_date.setDateTime(dt)

        item_id = tx.get("budget_item_id")
        bucket_id = next((i.get("bucket_id") for i in self.items_data if i.get("budget_item_id") == item_id), None)
        
        if bucket_id:
            idx_bucket = self.exp_bucket.findData(bucket_id)
            if idx_bucket >= 0: self.exp_bucket.setCurrentIndex(idx_bucket)
            
        idx_item = self.exp_item.findData(item_id)
        if idx_item >= 0: self.exp_item.setCurrentIndex(idx_item)
            
        idx_app = self.exp_approver.findData(tx.get("approver_id"))
        self.exp_approver.setCurrentIndex(idx_app if idx_app >= 0 else 0)

        self.exp_status.setCurrentText(tx.get("transaction_status", "Active"))
        self.exp_approval.setCurrentText(tx.get("approval_status", "Pending"))
        self.exp_receipt.setText(tx.get("receipt_path") or "")
        self.exp_notes.setText(tx.get("notes") or "")
        
        self.current_line_items = tx.get("line_items", []).copy()
        self.refresh_lines_ui()

    # --- CRUD ACTIONS ---
    def clear_current_form(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.current_payment_id = None
            self.pay_student.clear()
            self.pay_amount.setValue(0)
            self.pay_date.setDateTime(QDateTime.currentDateTime())
            self.pay_notes.clear()
            self.pay_approval.setCurrentIndex(0)
            self.pay_status.setCurrentIndex(0)
            self.pay_approver.setCurrentIndex(0)
            self.table_payments.clearSelection()
            self.filter_students()
        else:
            self.current_expense_id = None
            self.exp_date.setDateTime(QDateTime.currentDateTime())
            self.exp_receipt.clear()
            self.exp_notes.clear()
            self.exp_approval.setCurrentIndex(0)
            self.exp_status.setCurrentIndex(0)
            self.exp_approver.setCurrentIndex(0)
            self.current_line_items = []
            self.refresh_lines_ui()
            self.table_expenses.clearSelection()

    def save_current_form(self):
        idx = self.tabs.currentIndex()
        try:
            if idx == 0:  # PAYMENTS
                plan_id = self.pay_plan.currentData()
                if not plan_id: raise ValueError("Please select a Budget Plan.")

                student_text = self.pay_student.text().strip()
                student_id = self.student_mapping.get(student_text)
                
                if not student_id:
                    raise ValueError("Please select a valid student from the search suggestions.")

                data = {
                    "plan_id": plan_id,
                    "transaction_type": "PAYMENT",
                    "student_id": student_id,
                    "amount": self.pay_amount.value(),
                    "transaction_date": self.pay_date.dateTime().toString(Qt.DateFormat.ISODate),
                    "approval_status": self.pay_approval.currentText(),
                    "approver_id": self.pay_approver.currentData(),
                    "transaction_status": self.pay_status.currentText(),
                    "notes": self.pay_notes.text().strip()
                }

                if data["approval_status"] == "Approved" and not data.get("approver_id"):
                    raise ValueError("You must select an Officer to approve this transaction!")

                if self.current_payment_id: update_transaction(self.current_payment_id, data)
                else: create_transaction(data)

            else:  # EXPENSES
                plan_id = self.exp_plan.currentData()
                if not plan_id: raise ValueError("Please select a Budget Plan.")
                if not self.current_line_items: raise ValueError("Expenses require at least one Receipt Line Item.")

                computed_total = sum(item['quantity'] * item['unit_cost'] for item in self.current_line_items)

                data = {
                    "plan_id": plan_id,
                    "transaction_type": "EXPENSE",
                    "budget_item_id": self.exp_item.currentData(),
                    "line_items": self.current_line_items,
                    "amount": computed_total,
                    "transaction_date": self.exp_date.dateTime().toString(Qt.DateFormat.ISODate),
                    "approval_status": self.exp_approval.currentText(),
                    "approver_id": self.exp_approver.currentData(),
                    "transaction_status": self.exp_status.currentText(),
                    "receipt_path": self.exp_receipt.text().strip(),
                    "notes": self.exp_notes.text().strip()
                }

                if data["approval_status"] == "Approved" and not data.get("approver_id"):
                    raise ValueError("You must select an Officer to approve this transaction!")

                if self.current_expense_id: update_transaction(self.current_expense_id, data)
                else: create_transaction(data)

            self.load_all_data()
            self.clear_current_form()
            QMessageBox.information(self, "Success", "Transaction saved successfully.")

        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def delete_current_record(self):
        idx = self.tabs.currentIndex()
        target_id = self.current_payment_id if idx == 0 else self.current_expense_id
        target_type = "Payment" if idx == 0 else "Expense"
        
        if not target_id:
            QMessageBox.warning(self, "Selection Error", f"Please select a {target_type} to delete.")
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", 
                                    f"Are you sure you want to delete this {target_type}?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                    
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_transaction(target_id)
                self.load_all_data()
                self.clear_current_form()
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", str(e))