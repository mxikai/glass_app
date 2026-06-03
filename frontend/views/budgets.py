import sys
import os

# --- BRIDGE TO PROJECT ROOT ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.budget_service import (
    list_budget_plans, create_budget_plan, update_budget_plan, delete_budget_plan,
    list_fund_buckets, create_fund_bucket, update_fund_bucket, delete_fund_bucket,
    list_budget_items, create_budget_item, update_budget_item, delete_budget_item
)
# ----------------------------------

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, 
    QComboBox, QFrame, QDoubleSpinBox, QSpinBox, QTabWidget, QStackedWidget
)
from PyQt6.QtCore import Qt

class BudgetPlanView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        # State tracking
        self.current_plan_id = None
        self.current_bucket_id = None
        self.current_item_id = None
        
        self.plans_data = []
        self.buckets_data = []
        self.items_data = []

        self.setup_ui()
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
        
        title = QLabel("Budget Management")
        title.setObjectName("pageTitle")
        left_col.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("modernTabs")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        # 1. Plans Table
        self.table_plans = self._create_table(["ID", "Year", "Sem", "Budget", "Fee", "Status"])
        self.table_plans.itemSelectionChanged.connect(self.on_plan_select)
        self.tabs.addTab(self.table_plans, "1. Budget Plans")

        # 2. Buckets Table
        self.table_buckets = self._create_table(["ID", "Bucket Name", "Amount", "Description"])
        self.table_buckets.itemSelectionChanged.connect(self.on_bucket_select)
        self.tabs.addTab(self.table_buckets, "2. Fund Buckets")

        # 3. Items Table
        self.table_items = self._create_table(["ID", "Item Name", "Type", "Amount"])
        self.table_items.itemSelectionChanged.connect(self.on_item_select)
        self.tabs.addTab(self.table_items, "3. Budget Items")

        left_col.addWidget(self.tabs)

        # ==========================================
        # RIGHT COLUMN (Dynamic Form Panel)
        # ==========================================
        self.right_panel = QFrame()
        self.right_panel.setObjectName("profilePanel")
        self.right_panel.setFixedWidth(320)
        
        panel_layout = QVBoxLayout(self.right_panel)
        panel_layout.setContentsMargins(24, 32, 24, 32)
        panel_layout.setSpacing(16)
        
        self.form_title = QLabel("Plan Details")
        self.form_title.setObjectName("panelTitle")
        self.form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.form_title)

        # Use QStackedWidget to swap forms based on the active tab
        self.form_stack = QStackedWidget()
        
        self.setup_plan_form()
        self.setup_bucket_form()
        self.setup_item_form()
        
        panel_layout.addWidget(self.form_stack)
        panel_layout.addStretch()

        # Action Buttons
        self.btn_save = QPushButton("Save")
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

    # --- Form Setups ---
    def setup_plan_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setVerticalSpacing(12)
        
        self.plan_year = QLineEdit()
        self.plan_year.setPlaceholderText("e.g. 2025-2026")
        self.plan_sem = QComboBox()
        self.plan_sem.addItems(["1st", "2nd", "Midyear"])
        
        self.plan_budget = QDoubleSpinBox()
        self.plan_budget.setRange(0, 9999999)
        self.plan_budget.setPrefix("₱ ")
        
        self.plan_members = QSpinBox()
        self.plan_members.setRange(1, 5000)
        
        self.plan_status = QComboBox()
        self.plan_status.addItems(["Active", "Archived"])

        for w in [self.plan_year, self.plan_sem, self.plan_budget, self.plan_members, self.plan_status]:
            w.setObjectName("formInput")

        layout.addRow("Acad Year", self.plan_year)
        layout.addRow("Semester", self.plan_sem)
        layout.addRow("Total Budget", self.plan_budget)
        layout.addRow("Members", self.plan_members)
        layout.addRow("Status", self.plan_status)
        self.form_stack.addWidget(widget)

    def setup_bucket_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setVerticalSpacing(12)
        
        self.bucket_name = QLineEdit()
        self.bucket_amount = QDoubleSpinBox()
        self.bucket_amount.setRange(0, 9999999)
        self.bucket_amount.setPrefix("₱ ")
        self.bucket_desc = QLineEdit()

        for w in [self.bucket_name, self.bucket_amount, self.bucket_desc]:
            w.setObjectName("formInput")

        layout.addRow("Bucket Name", self.bucket_name)
        layout.addRow("Allocation", self.bucket_amount)
        layout.addRow("Description", self.bucket_desc)
        self.form_stack.addWidget(widget)

    def setup_item_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setVerticalSpacing(12)
        
        self.item_name = QLineEdit()
        self.item_type = QLineEdit()
        self.item_amount = QDoubleSpinBox()
        self.item_amount.setRange(0, 9999999)
        self.item_amount.setPrefix("₱ ")

        for w in [self.item_name, self.item_type, self.item_amount]:
            w.setObjectName("formInput")

        layout.addRow("Item Name", self.item_name)
        layout.addRow("Type", self.item_type)
        layout.addRow("Amount", self.item_amount)
        self.form_stack.addWidget(widget)

    # --- Data Loading ---
    def load_all_data(self):
        try:
            self.plans_data = list_budget_plans()
            self.buckets_data = list_fund_buckets()
            self.items_data = list_budget_items()
            
            self.refresh_plans_table()
            self.refresh_buckets_table()
            self.refresh_items_table()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load data: {e}")

    def refresh_plans_table(self):
        self.table_plans.setRowCount(0)
        for i, p in enumerate(self.plans_data):
            self.table_plans.insertRow(i)
            self.table_plans.setItem(i, 0, QTableWidgetItem(str(p.get("plan_id"))))
            self.table_plans.setItem(i, 1, QTableWidgetItem(p.get("academic_year")))
            self.table_plans.setItem(i, 2, QTableWidgetItem(p.get("semester")))
            self.table_plans.setItem(i, 3, QTableWidgetItem(f"₱{float(p.get('total_planned_budget') or 0):,.2f}"))
            self.table_plans.setItem(i, 4, QTableWidgetItem(f"₱{float(p.get('semestral_fee_amount') or 0):,.2f}"))
            self.table_plans.setItem(i, 5, QTableWidgetItem(p.get("status")))

    def refresh_buckets_table(self):
        self.table_buckets.setRowCount(0)
        if not self.current_plan_id: return
        
        filtered = [b for b in self.buckets_data if b.get("plan_id") == self.current_plan_id]
        for i, b in enumerate(filtered):
            self.table_buckets.insertRow(i)
            self.table_buckets.setItem(i, 0, QTableWidgetItem(str(b.get("bucket_id"))))
            self.table_buckets.setItem(i, 1, QTableWidgetItem(b.get("bucket_name")))
            self.table_buckets.setItem(i, 2, QTableWidgetItem(f"₱{float(b.get('planned_amount') or 0):,.2f}"))
            self.table_buckets.setItem(i, 3, QTableWidgetItem(b.get("description", "") or ""))

    def refresh_items_table(self):
        self.table_items.setRowCount(0)
        if not self.current_bucket_id: return
        
        filtered = [it for it in self.items_data if it.get("bucket_id") == self.current_bucket_id]
        for i, it in enumerate(filtered):
            self.table_items.insertRow(i)
            self.table_items.setItem(i, 0, QTableWidgetItem(str(it.get("budget_item_id"))))
            self.table_items.setItem(i, 1, QTableWidgetItem(it.get("item_name")))
            self.table_items.setItem(i, 2, QTableWidgetItem(it.get("item_type", "") or ""))
            self.table_items.setItem(i, 3, QTableWidgetItem(f"₱{float(it.get('planned_amount') or 0):,.2f}"))

    # --- UI Interactions ---
    def on_tab_changed(self, index):
        # SAFETY NET: If the UI is still building, do nothing and don't crash!
        if not hasattr(self, 'form_stack'):
            return 
            
        self.form_stack.setCurrentIndex(index)
        titles = ["Plan Details", "Bucket Details", "Item Details"]
        self.form_title.setText(titles[index])
        self.clear_current_form()

    def on_plan_select(self):
        rows = self.table_plans.selectedItems()
        if not rows: return
        
        self.current_plan_id = int(self.table_plans.item(rows[0].row(), 0).text())
        plan = next((p for p in self.plans_data if p["plan_id"] == self.current_plan_id), None)
        if plan:
            self.plan_year.setText(plan.get("academic_year", ""))
            self.plan_sem.setCurrentText(plan.get("semester", "1st"))
            self.plan_budget.setValue(float(plan.get("total_planned_budget") or 0))
            self.plan_members.setValue(int(plan.get("member_count") or 1))
            self.plan_status.setCurrentText(plan.get("status", "Active"))
            
        # Clear children selection and refresh their tables
        self.current_bucket_id = None
        self.current_item_id = None
        self.refresh_buckets_table()
        self.refresh_items_table()

    def on_bucket_select(self):
        rows = self.table_buckets.selectedItems()
        if not rows: return
        
        self.current_bucket_id = int(self.table_buckets.item(rows[0].row(), 0).text())
        bucket = next((b for b in self.buckets_data if b["bucket_id"] == self.current_bucket_id), None)
        if bucket:
            self.bucket_name.setText(bucket.get("bucket_name", ""))
            self.bucket_amount.setValue(float(bucket.get("planned_amount") or 0))
            self.bucket_desc.setText(bucket.get("description", ""))
            
        self.current_item_id = None
        self.refresh_items_table()

    def on_item_select(self):
        rows = self.table_items.selectedItems()
        if not rows: return
        
        self.current_item_id = int(self.table_items.item(rows[0].row(), 0).text())
        item = next((i for i in self.items_data if i["budget_item_id"] == self.current_item_id), None)
        if item:
            self.item_name.setText(item.get("item_name", ""))
            self.item_type.setText(item.get("item_type", ""))
            self.item_amount.setValue(float(item.get("planned_amount") or 0))

    # --- Save & Delete Logic ---
    def save_current_form(self):
        idx = self.tabs.currentIndex()
        try:
            if idx == 0:  # Save Plan
                if not self.plan_year.text(): raise ValueError("Academic Year is required.")
                data = {
                    "academic_year": self.plan_year.text().strip(),
                    "semester": self.plan_sem.currentText(),
                    "total_planned_budget": self.plan_budget.value(),
                    "member_count": self.plan_members.value(),
                    "status": self.plan_status.currentText()
                }
                if self.current_plan_id: update_budget_plan(self.current_plan_id, data)
                else: create_budget_plan(data)
                
            elif idx == 1:  # Save Bucket
                if not self.current_plan_id: raise ValueError("Select a Budget Plan first.")
                data = {
                    "plan_id": self.current_plan_id,
                    "bucket_name": self.bucket_name.text().strip(),
                    "planned_amount": self.bucket_amount.value(),
                    "description": self.bucket_desc.text().strip()
                }
                if self.current_bucket_id: update_fund_bucket(self.current_bucket_id, data)
                else: create_fund_bucket(data)
                
            elif idx == 2:  # Save Item
                if not self.current_bucket_id: raise ValueError("Select a Fund Bucket first.")
                data = {
                    "bucket_id": self.current_bucket_id,
                    "item_name": self.item_name.text().strip(),
                    "item_type": self.item_type.text().strip(),
                    "planned_amount": self.item_amount.value()
                }
                if self.current_item_id: update_budget_item(self.current_item_id, data)
                else: create_budget_item(data)

            self.load_all_data()
            self.clear_current_form()
        except Exception as e:
            QMessageBox.warning(self, "Validation Error", str(e))

    def clear_current_form(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.current_plan_id = None
            self.plan_year.clear()
            self.plan_sem.setCurrentIndex(0)
            self.plan_budget.setValue(0)
            self.plan_members.setValue(1)
            self.table_plans.clearSelection()
        elif idx == 1:
            self.current_bucket_id = None
            self.bucket_name.clear()
            self.bucket_amount.setValue(0)
            self.bucket_desc.clear()
            self.table_buckets.clearSelection()
        elif idx == 2:
            self.current_item_id = None
            self.item_name.clear()
            self.item_type.clear()
            self.item_amount.setValue(0)
            self.table_items.clearSelection()

    def delete_current_record(self):
        idx = self.tabs.currentIndex()
        target_id = [self.current_plan_id, self.current_bucket_id, self.current_item_id][idx]
        target_type = ["Plan", "Bucket", "Item"][idx]
        
        if not target_id:
            QMessageBox.warning(self, "Selection Error", f"Please select a {target_type} to delete.")
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", 
                                    f"Are you sure you want to delete this {target_type}? This will delete all connected data beneath it.",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                    
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if idx == 0: delete_budget_plan(target_id)
                elif idx == 1: delete_fund_bucket(target_id)
                elif idx == 2: delete_budget_item(target_id)
                
                self.load_all_data()
                self.clear_current_form()
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", str(e))