import sys
import os

# --- THE MASTER BRIDGE ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.budget_service import (
    list_budget_plans, create_budget_plan, update_budget_plan, delete_budget_plan,
    list_fund_buckets, create_fund_bucket, update_fund_bucket, delete_fund_bucket,
    list_budget_items, create_budget_item, update_budget_item, delete_budget_item
)
from backend.services.student_service import list_students 
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
        
        self.current_plan_id = None
        self.current_bucket_id = None
        self.current_item_id = None
        
        self.current_plan_student_ids = []
        
        self.plans_data = []
        self.buckets_data = []
        self.items_data = []
        self.students_data = []

        self.setup_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_all_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(24)

        # ==========================================
        # LEFT COLUMN
        # ==========================================
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        
        title = QLabel("Budget Management")
        title.setObjectName("pageTitle")
        left_col.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("modernTabs")
        self.tabs.currentChanged.connect(self.on_tab_changed)

        self.table_plans = self._create_table(["ID", "Year", "Sem", "Budget", "Fee", "Status"])
        self.table_plans.itemSelectionChanged.connect(self.on_plan_select)
        self.tabs.addTab(self.table_plans, "1. Budget Plans")

        self.table_buckets = self._create_table(["ID", "Bucket Name", "Amount", "Description"])
        self.table_buckets.itemSelectionChanged.connect(self.on_bucket_select)
        self.tabs.addTab(self.table_buckets, "2. Fund Buckets")

        self.table_items = self._create_table(["ID", "Item Name", "Type", "Amount"])
        self.table_items.itemSelectionChanged.connect(self.on_item_select)
        self.tabs.addTab(self.table_items, "3. Budget Items")

        left_col.addWidget(self.tabs)

        # ==========================================
        # RIGHT COLUMN
        # ==========================================
        self.right_panel = QFrame()
        self.right_panel.setObjectName("profilePanel")
        self.right_panel.setFixedWidth(400)
        
        panel_layout = QVBoxLayout(self.right_panel)
        panel_layout.setContentsMargins(24, 32, 24, 32)
        panel_layout.setSpacing(16)
        
        self.form_title = QLabel("Plan Details")
        self.form_title.setObjectName("panelTitle")
        self.form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(self.form_title)

        self.form_stack = QStackedWidget()
        
        self.setup_plan_form()
        self.setup_bucket_form()
        self.setup_item_form()
        
        panel_layout.addWidget(self.form_stack)
        panel_layout.addStretch()

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
        self.plan_members.setRange(0, 5000)
        self.plan_members.setReadOnly(True)
        self.plan_members.setToolTip("Shows the exact number of students historically saved to this plan.")
        
        self.btn_sync_students = QPushButton("↻ Sync Active Roster")
        self.btn_sync_students.setObjectName("secondaryBtn")
        self.btn_sync_students.setStyleSheet("font-size: 11px; padding: 6px;")
        self.btn_sync_students.clicked.connect(self.sync_active_students)
        
        member_layout = QHBoxLayout()
        member_layout.addWidget(self.plan_members)
        member_layout.addWidget(self.btn_sync_students)

        self.plan_status = QComboBox()
        self.plan_status.addItems(["Active", "Archived"])

        for w in [self.plan_year, self.plan_sem, self.plan_budget, self.plan_members, self.plan_status]:
            w.setObjectName("formInput")

        layout.addRow("Acad Year", self.plan_year)
        layout.addRow("Semester", self.plan_sem)
        layout.addRow("Total Budget", self.plan_budget)
        layout.addRow("Students", member_layout) 
        layout.addRow("Status", self.plan_status)
        
        self.form_stack.addWidget(widget)

    def setup_bucket_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setVerticalSpacing(12)
        
        self.bucket_plan_select = QComboBox()
        self.bucket_name = QLineEdit()
        self.bucket_amount = QDoubleSpinBox()
        self.bucket_amount.setRange(0, 9999999)
        self.bucket_amount.setPrefix("₱ ")
        self.bucket_desc = QLineEdit()

        for w in [self.bucket_plan_select, self.bucket_name, self.bucket_amount, self.bucket_desc]:
            w.setObjectName("formInput")

        layout.addRow("Budget Plan", self.bucket_plan_select)
        layout.addRow("Bucket Name", self.bucket_name)
        layout.addRow("Allocation", self.bucket_amount)
        layout.addRow("Description", self.bucket_desc)
        self.form_stack.addWidget(widget)

    def setup_item_form(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setVerticalSpacing(12)
        
        self.item_bucket_select = QComboBox()
        self.item_name = QLineEdit()
        self.item_type = QComboBox()
        self.item_type.addItems(["Activity", "Supply", "Service", "Equipment", "Inventory"])
        self.item_amount = QDoubleSpinBox()
        self.item_amount.setRange(0, 9999999)
        self.item_amount.setPrefix("₱ ")

        for w in [self.item_bucket_select, self.item_name, self.item_type, self.item_amount]:
            w.setObjectName("formInput")

        layout.addRow("Fund Bucket", self.item_bucket_select)
        layout.addRow("Item Name", self.item_name)
        layout.addRow("Type", self.item_type)
        layout.addRow("Amount", self.item_amount)
        self.form_stack.addWidget(widget)

    # --- CORE DATA METHODS ---
    def load_all_data(self):
        try:
            self.plans_data = list_budget_plans()
            self.buckets_data = list_fund_buckets()
            self.items_data = list_budget_items()
            self.students_data = list_students() 
            
            self.populate_dropdowns() 
            self.refresh_plans_table()
            self.refresh_buckets_table()
            self.refresh_items_table()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load data: {e}")

    def populate_dropdowns(self):
        curr_plan = self.bucket_plan_select.currentData()
        curr_bucket = self.item_bucket_select.currentData()

        self.bucket_plan_select.clear()
        self.bucket_plan_select.addItem("-- Select Budget Plan --", None)
        for p in self.plans_data:
            if isinstance(p, dict):
                label = f"Plan {p.get('plan_id')} ({p.get('academic_year')} Sem {p.get('semester')})"
                self.bucket_plan_select.addItem(label, p.get("plan_id"))

        self.item_bucket_select.clear()
        self.item_bucket_select.addItem("-- Select Fund Bucket --", None)
        for b in self.buckets_data:
            if isinstance(b, dict):
                label = f"{b.get('bucket_name')} (ID: {b.get('bucket_id')})"
                self.item_bucket_select.addItem(label, b.get("bucket_id"))

        if curr_plan:
            idx = self.bucket_plan_select.findData(curr_plan)
            if idx >= 0: self.bucket_plan_select.setCurrentIndex(idx)
        if curr_bucket:
            idx = self.item_bucket_select.findData(curr_bucket)
            if idx >= 0: self.item_bucket_select.setCurrentIndex(idx)

    # --- THE MAGIC SYNC METHOD ---
    def sync_active_students(self, silent=False):
        active_ids = [
            s.get("student_id") 
            for s in self.students_data 
            if isinstance(s, dict) and s.get("status") == "Active"
        ]
        
        self.current_plan_student_ids = active_ids
        self.plan_members.setValue(len(active_ids))
        
        if not silent:
            QMessageBox.information(self, "Roster Synced", f"Successfully pulled {len(active_ids)} active students into this plan.")

    # --- REFRESH TABLES ---
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
        
        if not self.current_plan_id:
            self.table_buckets.setRowCount(1)
            item = QTableWidgetItem("👈 Please select a Budget Plan in the first tab to view its Fund Buckets.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(Qt.GlobalColor.darkGray)
            self.table_buckets.setItem(0, 0, item)
            self.table_buckets.setSpan(0, 0, 1, self.table_buckets.columnCount())
            return
            
        filtered = [b for b in self.buckets_data if str(b.get("plan_id")) == str(self.current_plan_id)]
        
        if not filtered:
            self.table_buckets.setRowCount(1)
            item = QTableWidgetItem("No Fund Buckets found for this plan.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(Qt.GlobalColor.darkGray)
            self.table_buckets.setItem(0, 0, item)
            self.table_buckets.setSpan(0, 0, 1, self.table_buckets.columnCount())
            return
            
        for i, b in enumerate(filtered):
            self.table_buckets.insertRow(i)
            self.table_buckets.setItem(i, 0, QTableWidgetItem(str(b.get("bucket_id"))))
            self.table_buckets.setItem(i, 1, QTableWidgetItem(b.get("bucket_name")))
            self.table_buckets.setItem(i, 2, QTableWidgetItem(f"₱{float(b.get('planned_amount') or 0):,.2f}"))
            self.table_buckets.setItem(i, 3, QTableWidgetItem(b.get("description", "") or ""))

    def refresh_items_table(self):
        self.table_items.setRowCount(0)
        
        if not self.current_bucket_id:
            self.table_items.setRowCount(1)
            item = QTableWidgetItem("👈 Please select a Fund Bucket in the previous tab to view its Budget Items.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(Qt.GlobalColor.darkGray)
            self.table_items.setItem(0, 0, item)
            self.table_items.setSpan(0, 0, 1, self.table_items.columnCount())
            return
            
        filtered = [it for it in self.items_data if str(it.get("bucket_id")) == str(self.current_bucket_id)]
        
        if not filtered:
            self.table_items.setRowCount(1)
            item = QTableWidgetItem("No Budget Items found for this bucket.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(Qt.GlobalColor.darkGray)
            self.table_items.setItem(0, 0, item)
            self.table_items.setSpan(0, 0, 1, self.table_items.columnCount())
            return
            
        for i, it in enumerate(filtered):
            self.table_items.insertRow(i)
            self.table_items.setItem(i, 0, QTableWidgetItem(str(it.get("budget_item_id"))))
            self.table_items.setItem(i, 1, QTableWidgetItem(it.get("item_name")))
            self.table_items.setItem(i, 2, QTableWidgetItem(it.get("item_type", "") or ""))
            self.table_items.setItem(i, 3, QTableWidgetItem(f"₱{float(it.get('planned_amount') or 0):,.2f}"))

    def on_tab_changed(self, index):
        if not hasattr(self, 'form_stack'): return 
            
        self.form_stack.setCurrentIndex(index)
        titles = ["Plan Details", "Bucket Details", "Item Details"]
        self.form_title.setText(titles[index])
        
        # Force a table refresh to trigger the empty states if necessary
        self.refresh_buckets_table()
        self.refresh_items_table()

    def on_plan_select(self):
        rows = self.table_plans.selectedItems()
        if not rows: return
        
        self.current_plan_id = int(self.table_plans.item(rows[0].row(), 0).text())
        
        plan = None
        for p in self.plans_data:
            if isinstance(p, dict) and str(p.get("plan_id")) == str(self.current_plan_id):
                plan = p
                break
                
        if plan:
            self.plan_year.setText(plan.get("academic_year", ""))
            self.plan_sem.setCurrentText(plan.get("semester", "1st"))
            self.plan_budget.setValue(float(plan.get("total_planned_budget") or 0))
            self.plan_status.setCurrentText(plan.get("status", "Active"))
            
            self.current_plan_student_ids = plan.get("student_ids") or []
            self.plan_members.setValue(int(plan.get("member_count") or 0))
            
            idx = self.bucket_plan_select.findData(self.current_plan_id)
            if idx >= 0: self.bucket_plan_select.setCurrentIndex(idx)
            
        self.current_bucket_id = None
        self.current_item_id = None
        self.refresh_buckets_table()
        self.refresh_items_table()

    def on_bucket_select(self):
        rows = self.table_buckets.selectedItems()
        if not rows: return
        
        # Click protection: Ignore if they click the warning message row
        first_text = self.table_buckets.item(rows[0].row(), 0).text()
        if "👈" in first_text or "No Fund Buckets" in first_text:
            self.table_buckets.clearSelection()
            return
            
        self.current_bucket_id = int(first_text)
        
        bucket = None
        for b in self.buckets_data:
            if isinstance(b, dict) and str(b.get("bucket_id")) == str(self.current_bucket_id):
                bucket = b
                break
                
        if bucket:
            plan_idx = self.bucket_plan_select.findData(bucket.get("plan_id"))
            if plan_idx >= 0: self.bucket_plan_select.setCurrentIndex(plan_idx)
            
            item_idx = self.item_bucket_select.findData(self.current_bucket_id)
            if item_idx >= 0: self.item_bucket_select.setCurrentIndex(item_idx)

            self.bucket_name.setText(bucket.get("bucket_name", ""))
            self.bucket_amount.setValue(float(bucket.get("planned_amount") or 0))
            self.bucket_desc.setText(bucket.get("description", ""))
            
        self.current_item_id = None
        self.refresh_items_table()

    def on_item_select(self):
        rows = self.table_items.selectedItems()
        if not rows: return
        
        # Click protection: Ignore if they click the warning message row
        first_text = self.table_items.item(rows[0].row(), 0).text()
        if "👈" in first_text or "No Budget Items" in first_text:
            self.table_items.clearSelection()
            return
            
        self.current_item_id = int(first_text)
        
        item = None
        for i in self.items_data:
            if isinstance(i, dict) and str(i.get("budget_item_id")) == str(self.current_item_id):
                item = i
                break
                
        if item:
            bucket_idx = self.item_bucket_select.findData(item.get("bucket_id"))
            if bucket_idx >= 0: self.item_bucket_select.setCurrentIndex(bucket_idx)

            self.item_name.setText(item.get("item_name", ""))
            self.item_type.setCurrentText(item.get("item_type", "Activity") or "Activity")
            self.item_amount.setValue(float(item.get("planned_amount") or 0))

    def save_current_form(self):
        idx = self.tabs.currentIndex()
        try:
            if idx == 0:  
                if not self.plan_year.text(): raise ValueError("Academic Year is required.")
                
                if not self.current_plan_student_ids:
                    QMessageBox.warning(self, "Validation Error", "There are no students assigned to this plan. Try clicking Sync Active Roster.")
                    return

                data = {
                    "academic_year": self.plan_year.text().strip(),
                    "semester": self.plan_sem.currentText(),
                    "total_planned_budget": self.plan_budget.value(),
                    "member_count": len(self.current_plan_student_ids), 
                    "status": self.plan_status.currentText(),
                    "student_ids": self.current_plan_student_ids 
                }
                
                if self.current_plan_id: update_budget_plan(self.current_plan_id, data)
                else: create_budget_plan(data)
                
            elif idx == 1:  
                selected_plan_id = self.bucket_plan_select.currentData()
                if not selected_plan_id: raise ValueError("Please select a Budget Plan from the dropdown.")

                data = {
                    "plan_id": selected_plan_id,
                    "bucket_name": self.bucket_name.text().strip(),
                    "planned_amount": self.bucket_amount.value(),
                    "description": self.bucket_desc.text().strip()
                }
                if self.current_bucket_id: update_fund_bucket(self.current_bucket_id, data)
                else: create_fund_bucket(data)
                
            elif idx == 2:  
                selected_bucket_id = self.item_bucket_select.currentData()
                if not selected_bucket_id: raise ValueError("Please select a Fund Bucket from the dropdown.")

                data = {
                    "bucket_id": selected_bucket_id,
                    "item_name": self.item_name.text().strip(),
                    "item_type": self.item_type.currentText(), 
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
            
            self.sync_active_students(silent=True)
            self.table_plans.clearSelection()
            
            self.current_bucket_id = None
            self.current_item_id = None
            self.refresh_buckets_table()
            self.refresh_items_table()
            
        elif idx == 1:
            self.current_bucket_id = None
            self.bucket_plan_select.setCurrentIndex(0) 
            self.bucket_name.clear()
            self.bucket_amount.setValue(0)
            self.bucket_desc.clear()
            self.table_buckets.clearSelection()
            
            self.current_item_id = None
            self.refresh_items_table()
            
        elif idx == 2:
            self.current_item_id = None
            self.item_bucket_select.setCurrentIndex(0) 
            self.item_name.clear()
            self.item_type.setCurrentIndex(0)
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