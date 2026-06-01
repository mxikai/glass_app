from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.budget_service import (
    create_budget_item,
    create_budget_plan,
    create_fund_bucket,
    delete_budget_item,
    delete_budget_plan,
    delete_fund_bucket,
    list_budget_items,
    list_budget_plans,
    list_fund_buckets,
    update_budget_item,
    update_budget_plan,
    update_fund_bucket,
)
from services.inventory_service import (
    create_inventory_item,
    delete_inventory_item,
    list_inventory_items,
    update_inventory_item,
)
from services.student_service import (
    create_student,
    delete_student,
    list_students,
    update_student,
)
from services.transaction_service import (
    create_transaction,
    delete_transaction,
    list_transactions,
    update_transaction,
)
from utils.db import init_db


MoneyValue = int | float | str | None


def money(value: MoneyValue) -> str:
    try:
        amount = float(value or 0)
    except (TypeError, ValueError):
        amount = 0
    return f"PHP {amount:,.2f}"


def optional_text(widget: QLineEdit | QTextEdit) -> str | None:
    if isinstance(widget, QTextEdit):
        text = widget.toPlainText().strip()
    else:
        text = widget.text().strip()
    return text or None


def today_text() -> str:
    return date.today().isoformat()


def now_text() -> str:
    return datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes")


def table_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def set_combo_value(combo: QComboBox, value: Any) -> bool:
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            combo.setCurrentIndex(index)
            return True
    combo.setCurrentIndex(0)
    return False


def current_combo_value(combo: QComboBox) -> Any:
    return combo.currentData()


def set_combo_options(
    combo: QComboBox,
    rows: list[dict],
    value_key: str,
    label_fn: Callable[[dict], str],
    placeholder: str,
) -> None:
    selected = combo.currentData()
    combo.blockSignals(True)
    combo.clear()
    combo.addItem(placeholder, None)
    for row in rows:
        combo.addItem(label_fn(row), row.get(value_key))
    combo.blockSignals(False)
    if selected is not None:
        set_combo_value(combo, selected)


def make_money_input() -> QDoubleSpinBox:
    widget = QDoubleSpinBox()
    widget.setRange(0, 999_999_999)
    widget.setDecimals(2)
    widget.setPrefix("PHP ")
    widget.setSingleStep(100)
    widget.setAlignment(Qt.AlignRight)
    return widget


def make_quantity_input() -> QSpinBox:
    widget = QSpinBox()
    widget.setRange(1, 999_999)
    widget.setValue(1)
    widget.setAlignment(Qt.AlignRight)
    return widget


def make_status_combo(options: tuple[str, ...], editable: bool = False) -> QComboBox:
    combo = QComboBox()
    combo.addItems(options)
    combo.setEditable(editable)
    return combo


class DataTable(QTableWidget):
    def __init__(self, columns: list[tuple[str, str]], min_height: int = 180) -> None:
        super().__init__()
        self._columns = columns
        self._rows: list[dict] = []

        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels([label for _, label in columns])
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setMinimumHeight(min_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.horizontalHeader().setStretchLastSection(True)

    def set_rows(self, rows: list[dict]) -> None:
        self._rows = list(rows)
        self.blockSignals(True)
        self.clearContents()
        self.setColumnCount(len(self._columns))
        self.setHorizontalHeaderLabels([label for _, label in self._columns])
        self.setRowCount(len(self._rows))

        for row_index, row in enumerate(self._rows):
            for col_index, (key, _) in enumerate(self._columns):
                item = QTableWidgetItem(table_text(row.get(key)))
                item.setToolTip(table_text(row.get(key)))
                self.setItem(row_index, col_index, item)

        self.blockSignals(False)
        self.resizeColumnsToContents()

    def selected_record(self) -> dict | None:
        selected = self.selectionModel().selectedRows()
        if not selected:
            return None
        row_index = selected[0].row()
        if row_index < 0 or row_index >= len(self._rows):
            return None
        return self._rows[row_index]

    def select_record_by_key(self, key: str, value: Any) -> bool:
        for index, row in enumerate(self._rows):
            if row.get(key) == value:
                self.selectRow(index)
                return True
        self.clearSelection()
        return False


class WorkflowTab(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.status = QLabel("Ready.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #555;")

    def set_status(self, message: str) -> None:
        self.status.setText(message)

    def show_error(self, title: str, exc: Exception | str) -> None:
        message = str(exc)
        QMessageBox.critical(self, title, message)
        self.set_status(f"{title}: {message}")

    def confirm(self, title: str, message: str) -> bool:
        result = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return result == QMessageBox.Yes

    def refresh(self) -> None:
        pass


def make_scrollable_tab(layout: QVBoxLayout) -> QVBoxLayout:
    content = QWidget()
    content.setLayout(layout)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(content)

    wrapper = QVBoxLayout()
    wrapper.addWidget(scroll)
    return wrapper


class OverviewTab(WorkflowTab):
    def __init__(self) -> None:
        super().__init__()
        self.summary_labels: dict[str, QLabel] = {}
        self.recent_transactions = DataTable(
            [
                ("transaction_id", "ID"),
                ("transaction_type", "Type"),
                ("amount", "Amount"),
                ("student_id", "Student"),
                ("budget_item_id", "Budget Item"),
                ("approval_status", "Approval"),
                ("transaction_date", "Date"),
            ],
            min_height=260,
        )

        layout = QVBoxLayout()
        layout.setSpacing(16)

        header = QLabel("GLASS Budget Manager")
        header.setStyleSheet("font-size: 22px; font-weight: 700;")
        layout.addWidget(header)

        cards = QHBoxLayout()
        for key, label in [
            ("students", "Members"),
            ("officers", "Officers"),
            ("planned_budget", "Planned Budget"),
            ("fee", "Semestral Fee"),
            ("payments", "Payments"),
            ("expenses", "Expenses"),
            ("inventory", "Inventory"),
        ]:
            group = QGroupBox(label)
            group_layout = QVBoxLayout()
            value = QLabel("--")
            value.setStyleSheet("font-size: 18px; font-weight: 700;")
            group_layout.addWidget(value)
            group.setLayout(group_layout)
            cards.addWidget(group)
            self.summary_labels[key] = value
        layout.addLayout(cards)

        self.active_plan = QLabel("No active budget plan selected yet.")
        self.active_plan.setWordWrap(True)
        layout.addWidget(self.active_plan)

        recent_group = QGroupBox("Recent Transactions")
        recent_layout = QVBoxLayout()
        recent_layout.addWidget(self.recent_transactions)
        recent_group.setLayout(recent_layout)
        layout.addWidget(recent_group)
        layout.addWidget(self.status)

        self.setLayout(make_scrollable_tab(layout))

    def refresh(self) -> None:
        try:
            students = list_students()
            plans = list_budget_plans()
            transactions = list_transactions()
            inventory = list_inventory_items()
        except Exception as exc:
            self.show_error("Overview load failed", exc)
            return

        officers = [student for student in students if student.get("can_approve")]
        payments = [
            row
            for row in transactions
            if row.get("transaction_type") == "PAYMENT"
            and row.get("transaction_status", "Active") == "Active"
        ]
        expenses = [
            row
            for row in transactions
            if row.get("transaction_type") == "EXPENSE"
            and row.get("transaction_status", "Active") == "Active"
        ]
        active_plans = [plan for plan in plans if plan.get("status") == "Active"]
        selected_plan = active_plans[-1] if active_plans else plans[-1] if plans else None

        self.summary_labels["students"].setText(str(len(students)))
        self.summary_labels["officers"].setText(str(len(officers)))
        self.summary_labels["planned_budget"].setText(
            money(selected_plan.get("total_planned_budget") if selected_plan else 0)
        )
        self.summary_labels["fee"].setText(
            money(selected_plan.get("semestral_fee_amount") if selected_plan else 0)
        )
        self.summary_labels["payments"].setText(money(sum(row.get("amount") or 0 for row in payments)))
        self.summary_labels["expenses"].setText(money(sum(row.get("amount") or 0 for row in expenses)))
        self.summary_labels["inventory"].setText(str(len(inventory)))

        if selected_plan:
            self.active_plan.setText(
                "Active plan: "
                f"{selected_plan.get('academic_year')} {selected_plan.get('semester')} | "
                f"{selected_plan.get('member_count')} members | "
                f"{money(selected_plan.get('semestral_fee_amount'))} each"
            )
        else:
            self.active_plan.setText("No budget plan has been created yet.")

        recent = sorted(
            transactions,
            key=lambda row: row.get("transaction_date") or "",
            reverse=True,
        )[:10]
        self.recent_transactions.set_rows(recent)
        self.set_status("Overview refreshed.")


class MembersTab(WorkflowTab):
    def __init__(self) -> None:
        super().__init__()
        self.students: list[dict] = []

        self.table = DataTable(
            [
                ("student_id", "Student ID"),
                ("name", "Name"),
                ("role_title", "Role"),
                ("can_approve", "Approver"),
                ("status", "Status"),
                ("program", "Program"),
                ("year_level", "Year"),
            ],
            min_height=300,
        )
        self.table.itemSelectionChanged.connect(self.load_selected)

        self.student_id = QLineEdit()
        self.name = QLineEdit()
        self.program = QLineEdit()
        self.year_level = QComboBox()
        self.year_level.addItem("", None)
        for year in range(1, 7):
            self.year_level.addItem(str(year), year)
        self.role_title = QLineEdit()
        self.can_approve = QCheckBox("Can approve organization transactions")
        self.status_combo = make_status_combo(("Active", "Inactive", "Alumni"), editable=True)

        form = QFormLayout()
        form.addRow("Student ID", self.student_id)
        form.addRow("Name", self.name)
        form.addRow("Program", self.program)
        form.addRow("Year Level", self.year_level)
        form.addRow("Officer Role", self.role_title)
        form.addRow("", self.can_approve)
        form.addRow("Status", self.status_combo)

        form_group = QGroupBox("Member Details")
        form_group.setLayout(form)

        save_button = QPushButton("Save Member")
        save_button.clicked.connect(self.save_member)
        new_button = QPushButton("New")
        new_button.clicked.connect(self.clear_form)
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_selected)

        buttons = QHBoxLayout()
        buttons.addWidget(save_button)
        buttons.addWidget(new_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(QLabel("Students are the organization members. Officers are students with roles and approval authority."))
        layout.addWidget(self.table)
        layout.addWidget(form_group)
        layout.addLayout(buttons)
        layout.addWidget(self.status)
        self.setLayout(make_scrollable_tab(layout))

    def refresh(self) -> None:
        try:
            self.students = list_students()
        except Exception as exc:
            self.show_error("Members load failed", exc)
            return
        self.table.set_rows(self.students)
        self.set_status(f"Loaded {len(self.students)} member(s).")

    def load_selected(self) -> None:
        row = self.table.selected_record()
        if not row:
            return
        self.student_id.setText(row.get("student_id") or "")
        self.name.setText(row.get("name") or "")
        self.program.setText(row.get("program") or "")
        set_combo_value(self.year_level, row.get("year_level"))
        self.role_title.setText(row.get("role_title") or "")
        self.can_approve.setChecked(bool(row.get("can_approve")))
        self.status_combo.setCurrentText(row.get("status") or "Active")

    def clear_form(self) -> None:
        self.table.clearSelection()
        self.student_id.clear()
        self.name.clear()
        self.program.clear()
        self.year_level.setCurrentIndex(0)
        self.role_title.clear()
        self.can_approve.setChecked(False)
        self.status_combo.setCurrentText("Active")
        self.set_status("Ready for a new member.")

    def save_member(self) -> None:
        student_id = self.student_id.text().strip()
        name = self.name.text().strip()
        if not student_id or not name:
            self.show_error("Member save failed", "Student ID and name are required.")
            return

        payload = {
            "student_id": student_id,
            "name": name,
            "program": optional_text(self.program),
            "year_level": current_combo_value(self.year_level),
            "role_title": optional_text(self.role_title),
            "can_approve": self.can_approve.isChecked(),
            "status": self.status_combo.currentText().strip() or "Active",
        }
        exists = any(student.get("student_id") == student_id for student in self.students)

        try:
            if exists:
                update_payload = {key: value for key, value in payload.items() if key != "student_id"}
                update_student(student_id, update_payload)
                self.set_status(f"Updated member {student_id}.")
            else:
                create_student(payload)
                self.set_status(f"Created member {student_id}.")
        except Exception as exc:
            self.show_error("Member save failed", exc)
            return

        self.refresh()
        self.table.select_record_by_key("student_id", student_id)

    def delete_selected(self) -> None:
        row = self.table.selected_record()
        if not row:
            self.show_error("Delete failed", "Select a member first.")
            return
        student_id = row.get("student_id")
        if not self.confirm("Delete Member", f"Delete {student_id}? This cannot be undone."):
            return
        try:
            deleted = delete_student(student_id)
        except Exception as exc:
            self.show_error("Delete failed", exc)
            return
        if not deleted:
            self.show_error("Delete failed", "Member was not found.")
            return
        self.clear_form()
        self.refresh()


class BudgetPlanningTab(WorkflowTab):
    def __init__(self) -> None:
        super().__init__()
        self.students: list[dict] = []
        self.plans: list[dict] = []
        self.buckets: list[dict] = []
        self.items: list[dict] = []
        self.current_plan_id: int | None = None
        self.current_bucket_id: int | None = None
        self.current_item_id: int | None = None

        self.plan_table = DataTable(
            [
                ("plan_id", "ID"),
                ("academic_year", "Academic Year"),
                ("semester", "Semester"),
                ("total_planned_budget", "Budget"),
                ("member_count", "Members"),
                ("semestral_fee_amount", "Fee"),
                ("approval_status", "Approval"),
                ("status", "Status"),
            ],
            min_height=210,
        )
        self.bucket_table = DataTable(
            [
                ("bucket_id", "ID"),
                ("bucket_name", "Bucket"),
                ("planned_amount", "Planned"),
                ("description", "Description"),
            ],
            min_height=190,
        )
        self.item_table = DataTable(
            [
                ("budget_item_id", "ID"),
                ("item_name", "Item"),
                ("item_type", "Type"),
                ("planned_amount", "Planned"),
                ("description", "Description"),
            ],
            min_height=190,
        )
        self.plan_table.itemSelectionChanged.connect(self.load_selected_plan)
        self.bucket_table.itemSelectionChanged.connect(self.load_selected_bucket)
        self.item_table.itemSelectionChanged.connect(self.load_selected_item)

        self.plan_id = QLineEdit()
        self.plan_id.setReadOnly(True)
        self.academic_year = QLineEdit()
        self.academic_year.setPlaceholderText("2025-2026")
        self.semester = make_status_combo(("1st", "2nd", "Midyear"), editable=True)
        self.total_budget = make_money_input()
        self.approval_status = make_status_combo(("Pending", "Approved", "Rejected"), editable=True)
        self.approved_date = QLineEdit()
        self.approved_date.setPlaceholderText("YYYY-MM-DD")
        self.plan_status = make_status_combo(("Active", "Archived"), editable=True)
        self.member_list = QListWidget()
        self.member_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.member_list.setMinimumHeight(150)
        self.member_count = QLabel("0 members")
        self.fee_preview = QLabel("PHP 0.00")
        self.member_list.itemSelectionChanged.connect(self.update_plan_preview)
        self.total_budget.valueChanged.connect(self.update_plan_preview)

        plan_form = QFormLayout()
        plan_form.addRow("Plan ID", self.plan_id)
        plan_form.addRow("Academic Year", self.academic_year)
        plan_form.addRow("Semester", self.semester)
        plan_form.addRow("Total Planned Budget", self.total_budget)
        plan_form.addRow("Approval Status", self.approval_status)
        plan_form.addRow("Approved Date", self.approved_date)
        plan_form.addRow("Status", self.plan_status)
        plan_form.addRow("Students in Plan", self.member_list)
        plan_form.addRow("Member Count", self.member_count)
        plan_form.addRow("Derived Semestral Fee", self.fee_preview)

        plan_group = QGroupBox("Semestral Budget Plan")
        plan_group.setLayout(plan_form)

        save_plan = QPushButton("Save Plan")
        save_plan.clicked.connect(self.save_plan)
        new_plan = QPushButton("New Plan")
        new_plan.clicked.connect(self.clear_plan_form)
        delete_plan = QPushButton("Delete Plan")
        delete_plan.clicked.connect(self.delete_current_plan)
        plan_buttons = QHBoxLayout()
        plan_buttons.addWidget(save_plan)
        plan_buttons.addWidget(new_plan)
        plan_buttons.addWidget(delete_plan)
        plan_buttons.addStretch()

        self.bucket_id = QLineEdit()
        self.bucket_id.setReadOnly(True)
        self.bucket_name = QLineEdit()
        self.bucket_amount = make_money_input()
        self.bucket_description = QLineEdit()
        bucket_form = QFormLayout()
        bucket_form.addRow("Bucket ID", self.bucket_id)
        bucket_form.addRow("Name", self.bucket_name)
        bucket_form.addRow("Planned Amount", self.bucket_amount)
        bucket_form.addRow("Description", self.bucket_description)
        bucket_group = QGroupBox("Fund Bucket")
        bucket_group.setLayout(bucket_form)

        save_bucket = QPushButton("Save Bucket")
        save_bucket.clicked.connect(self.save_bucket)
        new_bucket = QPushButton("New Bucket")
        new_bucket.clicked.connect(self.clear_bucket_form)
        delete_bucket = QPushButton("Delete Bucket")
        delete_bucket.clicked.connect(self.delete_current_bucket)
        bucket_buttons = QHBoxLayout()
        bucket_buttons.addWidget(save_bucket)
        bucket_buttons.addWidget(new_bucket)
        bucket_buttons.addWidget(delete_bucket)
        bucket_buttons.addStretch()

        self.item_id = QLineEdit()
        self.item_id.setReadOnly(True)
        self.item_name = QLineEdit()
        self.item_type = QLineEdit()
        self.item_amount = make_money_input()
        self.item_description = QLineEdit()
        item_form = QFormLayout()
        item_form.addRow("Item ID", self.item_id)
        item_form.addRow("Name", self.item_name)
        item_form.addRow("Type", self.item_type)
        item_form.addRow("Planned Amount", self.item_amount)
        item_form.addRow("Description", self.item_description)
        item_group = QGroupBox("Budget Item")
        item_group.setLayout(item_form)

        save_item = QPushButton("Save Item")
        save_item.clicked.connect(self.save_item)
        new_item = QPushButton("New Item")
        new_item.clicked.connect(self.clear_item_form)
        delete_item = QPushButton("Delete Item")
        delete_item.clicked.connect(self.delete_current_item)
        item_buttons = QHBoxLayout()
        item_buttons.addWidget(save_item)
        item_buttons.addWidget(new_item)
        item_buttons.addWidget(delete_item)
        item_buttons.addStretch()

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(QLabel("Build the approved semester plan first, then split it into fund buckets and budget items."))
        layout.addWidget(self.plan_table)
        layout.addWidget(plan_group)
        layout.addLayout(plan_buttons)
        layout.addWidget(self.bucket_table)
        layout.addWidget(bucket_group)
        layout.addLayout(bucket_buttons)
        layout.addWidget(self.item_table)
        layout.addWidget(item_group)
        layout.addLayout(item_buttons)
        layout.addWidget(self.status)
        self.setLayout(make_scrollable_tab(layout))

    def refresh(self) -> None:
        try:
            self.students = list_students()
            self.plans = list_budget_plans()
            self.buckets = list_fund_buckets()
            self.items = list_budget_items()
        except Exception as exc:
            self.show_error("Budget planning load failed", exc)
            return

        current_plan = self.current_plan_id
        self.plan_table.set_rows(self.plans)
        self.populate_member_list()

        if current_plan and self.plan_table.select_record_by_key("plan_id", current_plan):
            pass
        elif self.plans:
            self.current_plan_id = self.plans[-1]["plan_id"]
            self.plan_table.select_record_by_key("plan_id", self.current_plan_id)
        else:
            self.clear_plan_form()
            self.refresh_bucket_table()

        self.set_status(
            f"Loaded {len(self.plans)} plan(s), {len(self.buckets)} bucket(s), "
            f"and {len(self.items)} item(s)."
        )

    def populate_member_list(self) -> None:
        selected_ids = set(self.selected_student_ids())
        self.member_list.blockSignals(True)
        self.member_list.clear()
        for student in self.students:
            label = f"{student.get('student_id')} - {student.get('name')}"
            if student.get("role_title"):
                label += f" ({student.get('role_title')})"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, student.get("student_id"))
            self.member_list.addItem(item)
            item.setSelected(student.get("student_id") in selected_ids)
        self.member_list.blockSignals(False)

    def selected_student_ids(self) -> list[str]:
        return [item.data(Qt.UserRole) for item in self.member_list.selectedItems()]

    def select_student_ids(self, student_ids: list[str]) -> None:
        selected = set(student_ids)
        self.member_list.blockSignals(True)
        for index in range(self.member_list.count()):
            item = self.member_list.item(index)
            item.setSelected(item.data(Qt.UserRole) in selected)
        self.member_list.blockSignals(False)
        self.update_plan_preview()

    def update_plan_preview(self) -> None:
        count = len(self.selected_student_ids())
        self.member_count.setText(f"{count} member(s)")
        fee = self.total_budget.value() / count if count else 0
        self.fee_preview.setText(money(fee))

    def load_selected_plan(self) -> None:
        row = self.plan_table.selected_record()
        if not row:
            return
        self.current_plan_id = row.get("plan_id")
        self.plan_id.setText(str(row.get("plan_id") or ""))
        self.academic_year.setText(row.get("academic_year") or "")
        self.semester.setCurrentText(row.get("semester") or "1st")
        self.total_budget.setValue(float(row.get("total_planned_budget") or 0))
        self.approval_status.setCurrentText(row.get("approval_status") or "Pending")
        self.approved_date.setText(row.get("approved_date") or "")
        self.plan_status.setCurrentText(row.get("status") or "Active")
        self.select_student_ids(row.get("student_ids") or [])
        self.clear_bucket_form()
        self.refresh_bucket_table()

    def clear_plan_form(self) -> None:
        self.current_plan_id = None
        self.plan_table.clearSelection()
        self.plan_id.clear()
        self.academic_year.clear()
        self.semester.setCurrentText("1st")
        self.total_budget.setValue(0)
        self.approval_status.setCurrentText("Pending")
        self.approved_date.clear()
        self.plan_status.setCurrentText("Active")
        self.select_student_ids([])
        self.clear_bucket_form()
        self.refresh_bucket_table()
        self.set_status("Ready for a new budget plan.")

    def save_plan(self) -> None:
        student_ids = self.selected_student_ids()
        if not self.academic_year.text().strip() or not self.semester.currentText().strip():
            self.show_error("Plan save failed", "Academic year and semester are required.")
            return
        if self.total_budget.value() <= 0:
            self.show_error("Plan save failed", "Total planned budget must be greater than 0.")
            return
        if not student_ids:
            self.show_error("Plan save failed", "Select at least one student for the semester.")
            return

        payload = {
            "academic_year": self.academic_year.text().strip(),
            "semester": self.semester.currentText().strip(),
            "total_planned_budget": self.total_budget.value(),
            "member_count": len(student_ids),
            "approval_status": self.approval_status.currentText().strip() or "Pending",
            "approved_date": optional_text(self.approved_date),
            "status": self.plan_status.currentText().strip() or "Active",
            "student_ids": student_ids,
        }

        try:
            if self.current_plan_id:
                plan = update_budget_plan(self.current_plan_id, payload)
                if not plan:
                    raise ValueError("Plan was not found.")
                self.set_status(f"Updated plan #{self.current_plan_id}.")
            else:
                plan = create_budget_plan(payload)
                self.current_plan_id = plan["plan_id"]
                self.set_status(f"Created plan #{self.current_plan_id}.")
        except Exception as exc:
            self.show_error("Plan save failed", exc)
            return

        self.refresh()
        self.plan_table.select_record_by_key("plan_id", self.current_plan_id)

    def delete_current_plan(self) -> None:
        if not self.current_plan_id:
            self.show_error("Delete failed", "Select a budget plan first.")
            return
        if not self.confirm("Delete Budget Plan", f"Delete plan #{self.current_plan_id} and its related records?"):
            return
        try:
            deleted = delete_budget_plan(self.current_plan_id)
        except Exception as exc:
            self.show_error("Delete failed", exc)
            return
        if not deleted:
            self.show_error("Delete failed", "Plan was not found.")
            return
        self.current_plan_id = None
        self.refresh()

    def refresh_bucket_table(self) -> None:
        if not self.current_plan_id:
            self.bucket_table.set_rows([])
            self.item_table.set_rows([])
            return

        rows = [bucket for bucket in self.buckets if bucket.get("plan_id") == self.current_plan_id]
        self.bucket_table.set_rows(rows)
        if self.current_bucket_id and self.bucket_table.select_record_by_key("bucket_id", self.current_bucket_id):
            return
        if rows:
            self.current_bucket_id = rows[0]["bucket_id"]
            self.bucket_table.select_record_by_key("bucket_id", self.current_bucket_id)
        else:
            self.clear_bucket_form()
            self.refresh_item_table()

    def load_selected_bucket(self) -> None:
        row = self.bucket_table.selected_record()
        if not row:
            return
        self.current_bucket_id = row.get("bucket_id")
        self.bucket_id.setText(str(row.get("bucket_id") or ""))
        self.bucket_name.setText(row.get("bucket_name") or "")
        self.bucket_amount.setValue(float(row.get("planned_amount") or 0))
        self.bucket_description.setText(row.get("description") or "")
        self.clear_item_form()
        self.refresh_item_table()

    def clear_bucket_form(self) -> None:
        self.current_bucket_id = None
        self.bucket_table.clearSelection()
        self.bucket_id.clear()
        self.bucket_name.clear()
        self.bucket_amount.setValue(0)
        self.bucket_description.clear()
        self.clear_item_form()

    def save_bucket(self) -> None:
        if not self.current_plan_id:
            self.show_error("Bucket save failed", "Select a budget plan first.")
            return
        if not self.bucket_name.text().strip() or self.bucket_amount.value() <= 0:
            self.show_error("Bucket save failed", "Bucket name and planned amount are required.")
            return
        payload = {
            "bucket_name": self.bucket_name.text().strip(),
            "planned_amount": self.bucket_amount.value(),
            "description": optional_text(self.bucket_description),
        }
        try:
            if self.current_bucket_id:
                bucket = update_fund_bucket(self.current_bucket_id, payload)
                if not bucket:
                    raise ValueError("Bucket was not found.")
                self.set_status(f"Updated bucket #{self.current_bucket_id}.")
            else:
                bucket = create_fund_bucket({"plan_id": self.current_plan_id, **payload})
                self.current_bucket_id = bucket["bucket_id"]
                self.set_status(f"Created bucket #{self.current_bucket_id}.")
        except Exception as exc:
            self.show_error("Bucket save failed", exc)
            return
        self.refresh()
        self.bucket_table.select_record_by_key("bucket_id", self.current_bucket_id)

    def delete_current_bucket(self) -> None:
        if not self.current_bucket_id:
            self.show_error("Delete failed", "Select a fund bucket first.")
            return
        if not self.confirm("Delete Fund Bucket", f"Delete bucket #{self.current_bucket_id}?"):
            return
        try:
            deleted = delete_fund_bucket(self.current_bucket_id)
        except Exception as exc:
            self.show_error("Delete failed", exc)
            return
        if not deleted:
            self.show_error("Delete failed", "Bucket was not found.")
            return
        self.current_bucket_id = None
        self.refresh()

    def refresh_item_table(self) -> None:
        if not self.current_bucket_id:
            self.item_table.set_rows([])
            return
        rows = [item for item in self.items if item.get("bucket_id") == self.current_bucket_id]
        self.item_table.set_rows(rows)
        if self.current_item_id and self.item_table.select_record_by_key("budget_item_id", self.current_item_id):
            return
        if rows:
            self.current_item_id = rows[0]["budget_item_id"]
            self.item_table.select_record_by_key("budget_item_id", self.current_item_id)
        else:
            self.clear_item_form()

    def load_selected_item(self) -> None:
        row = self.item_table.selected_record()
        if not row:
            return
        self.current_item_id = row.get("budget_item_id")
        self.item_id.setText(str(row.get("budget_item_id") or ""))
        self.item_name.setText(row.get("item_name") or "")
        self.item_type.setText(row.get("item_type") or "")
        self.item_amount.setValue(float(row.get("planned_amount") or 0))
        self.item_description.setText(row.get("description") or "")

    def clear_item_form(self) -> None:
        self.current_item_id = None
        self.item_table.clearSelection()
        self.item_id.clear()
        self.item_name.clear()
        self.item_type.clear()
        self.item_amount.setValue(0)
        self.item_description.clear()

    def save_item(self) -> None:
        if not self.current_bucket_id:
            self.show_error("Item save failed", "Select a fund bucket first.")
            return
        if not self.item_name.text().strip() or self.item_amount.value() <= 0:
            self.show_error("Item save failed", "Item name and planned amount are required.")
            return
        payload = {
            "item_name": self.item_name.text().strip(),
            "item_type": optional_text(self.item_type),
            "planned_amount": self.item_amount.value(),
            "description": optional_text(self.item_description),
        }
        try:
            if self.current_item_id:
                item = update_budget_item(self.current_item_id, payload)
                if not item:
                    raise ValueError("Budget item was not found.")
                self.set_status(f"Updated item #{self.current_item_id}.")
            else:
                item = create_budget_item({"bucket_id": self.current_bucket_id, **payload})
                self.current_item_id = item["budget_item_id"]
                self.set_status(f"Created item #{self.current_item_id}.")
        except Exception as exc:
            self.show_error("Item save failed", exc)
            return
        self.refresh()
        self.item_table.select_record_by_key("budget_item_id", self.current_item_id)

    def delete_current_item(self) -> None:
        if not self.current_item_id:
            self.show_error("Delete failed", "Select a budget item first.")
            return
        if not self.confirm("Delete Budget Item", f"Delete item #{self.current_item_id}?"):
            return
        try:
            deleted = delete_budget_item(self.current_item_id)
        except Exception as exc:
            self.show_error("Delete failed", exc)
            return
        if not deleted:
            self.show_error("Delete failed", "Budget item was not found.")
            return
        self.current_item_id = None
        self.refresh()


class TransactionsTab(WorkflowTab):
    def __init__(self) -> None:
        super().__init__()
        self.plans: list[dict] = []
        self.students: list[dict] = []
        self.buckets: list[dict] = []
        self.items: list[dict] = []
        self.transactions: list[dict] = []
        self.inventory: list[dict] = []
        self.current_payment_id: int | None = None
        self.current_expense_id: int | None = None

        self.table = DataTable(
            [
                ("transaction_id", "ID"),
                ("transaction_type", "Type"),
                ("amount", "Amount"),
                ("student_id", "Student"),
                ("budget_item_id", "Budget Item"),
                ("approver_id", "Approver"),
                ("approval_status", "Approval"),
                ("transaction_status", "Status"),
                ("transaction_date", "Date"),
            ],
            min_height=260,
        )
        self.table.itemSelectionChanged.connect(self.load_selected_transaction)

        self.payment_id = QLineEdit()
        self.payment_id.setReadOnly(True)
        self.payment_plan = QComboBox()
        self.payment_student = QComboBox()
        self.payment_amount = make_money_input()
        self.payment_approver = QComboBox()
        self.payment_approval = make_status_combo(("Pending", "Approved", "Rejected"), editable=True)
        self.payment_status = make_status_combo(("Active", "Void"), editable=True)
        self.payment_date = QLineEdit(now_text())
        self.payment_notes = QTextEdit()
        self.payment_notes.setFixedHeight(70)
        self.payment_plan.currentIndexChanged.connect(self.default_payment_amount)

        payment_form = QFormLayout()
        payment_form.addRow("Transaction ID", self.payment_id)
        payment_form.addRow("Budget Plan", self.payment_plan)
        payment_form.addRow("Student", self.payment_student)
        payment_form.addRow("Amount", self.payment_amount)
        payment_form.addRow("Approver", self.payment_approver)
        payment_form.addRow("Approval", self.payment_approval)
        payment_form.addRow("Status", self.payment_status)
        payment_form.addRow("Date/Time", self.payment_date)
        payment_form.addRow("Notes", self.payment_notes)
        payment_group = QGroupBox("Payment")
        payment_group.setLayout(payment_form)

        save_payment = QPushButton("Save Payment")
        save_payment.clicked.connect(self.save_payment)
        new_payment = QPushButton("New Payment")
        new_payment.clicked.connect(self.clear_payment_form)
        payment_buttons = QHBoxLayout()
        payment_buttons.addWidget(save_payment)
        payment_buttons.addWidget(new_payment)
        payment_buttons.addStretch()

        self.expense_id = QLineEdit()
        self.expense_id.setReadOnly(True)
        self.expense_plan = QComboBox()
        self.expense_item = QComboBox()
        self.expense_amount = make_money_input()
        self.expense_approver = QComboBox()
        self.expense_approval = make_status_combo(("Pending", "Approved", "Rejected"), editable=True)
        self.expense_status = make_status_combo(("Active", "Void"), editable=True)
        self.expense_date = QLineEdit(now_text())
        self.expense_receipt = QLineEdit()
        self.expense_notes = QTextEdit()
        self.expense_notes.setFixedHeight(70)
        self.capture_inventory = QCheckBox("Record one inventory item from this purchase")
        self.inventory_name = QLineEdit()
        self.inventory_quantity = make_quantity_input()
        self.inventory_condition = make_status_combo(("New", "Good", "Needs Repair", "Retired"), editable=True)
        self.inventory_status = make_status_combo(("Active", "Archived"), editable=True)
        self.inventory_date = QLineEdit(today_text())
        self.expense_plan.currentIndexChanged.connect(self.refresh_expense_items)
        self.expense_item.currentIndexChanged.connect(self.default_expense_amount)
        self.capture_inventory.stateChanged.connect(self.sync_inventory_fields)

        expense_form = QFormLayout()
        expense_form.addRow("Transaction ID", self.expense_id)
        expense_form.addRow("Budget Plan", self.expense_plan)
        expense_form.addRow("Budget Item", self.expense_item)
        expense_form.addRow("Amount", self.expense_amount)
        expense_form.addRow("Approver", self.expense_approver)
        expense_form.addRow("Approval", self.expense_approval)
        expense_form.addRow("Status", self.expense_status)
        expense_form.addRow("Date/Time", self.expense_date)
        expense_form.addRow("Receipt Path", self.expense_receipt)
        expense_form.addRow("Notes", self.expense_notes)
        expense_form.addRow("", self.capture_inventory)
        expense_form.addRow("Inventory Name", self.inventory_name)
        expense_form.addRow("Quantity", self.inventory_quantity)
        expense_form.addRow("Condition", self.inventory_condition)
        expense_form.addRow("Inventory Status", self.inventory_status)
        expense_form.addRow("Date Recorded", self.inventory_date)
        expense_group = QGroupBox("Expense")
        expense_group.setLayout(expense_form)

        save_expense = QPushButton("Save Expense")
        save_expense.clicked.connect(self.save_expense)
        new_expense = QPushButton("New Expense")
        new_expense.clicked.connect(self.clear_expense_form)
        expense_buttons = QHBoxLayout()
        expense_buttons.addWidget(save_expense)
        expense_buttons.addWidget(new_expense)
        expense_buttons.addStretch()

        delete_transaction = QPushButton("Delete Selected Transaction")
        delete_transaction.clicked.connect(self.delete_selected_transaction)

        forms = QHBoxLayout()
        forms.addWidget(payment_group)
        forms.addWidget(expense_group)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(QLabel("Record student semestral fee payments and approved organization expenses."))
        layout.addWidget(self.table)
        layout.addWidget(delete_transaction)
        layout.addLayout(forms)
        layout.addLayout(payment_buttons)
        layout.addLayout(expense_buttons)
        layout.addWidget(self.status)
        self.setLayout(make_scrollable_tab(layout))
        self.sync_inventory_fields()

    def refresh(self) -> None:
        try:
            self.plans = list_budget_plans()
            self.students = list_students()
            self.buckets = list_fund_buckets()
            self.items = list_budget_items()
            self.transactions = list_transactions()
            self.inventory = list_inventory_items()
        except Exception as exc:
            self.show_error("Transactions load failed", exc)
            return

        set_combo_options(
            self.payment_plan,
            self.plans,
            "plan_id",
            lambda row: f"#{row.get('plan_id')} {row.get('academic_year')} {row.get('semester')} - {money(row.get('semestral_fee_amount'))}",
            "Select plan",
        )
        set_combo_options(
            self.expense_plan,
            self.plans,
            "plan_id",
            lambda row: f"#{row.get('plan_id')} {row.get('academic_year')} {row.get('semester')}",
            "Select plan",
        )
        set_combo_options(
            self.payment_student,
            self.students,
            "student_id",
            lambda row: f"{row.get('student_id')} - {row.get('name')}",
            "Select student",
        )
        approvers = [student for student in self.students if student.get("can_approve")]
        set_combo_options(
            self.payment_approver,
            approvers,
            "student_id",
            lambda row: f"{row.get('student_id')} - {row.get('name')}",
            "No approver",
        )
        set_combo_options(
            self.expense_approver,
            approvers,
            "student_id",
            lambda row: f"{row.get('student_id')} - {row.get('name')}",
            "No approver",
        )
        self.refresh_expense_items()

        rows = sorted(
            self.transactions,
            key=lambda row: row.get("transaction_date") or "",
            reverse=True,
        )
        self.table.set_rows(rows)
        self.set_status(f"Loaded {len(rows)} transaction(s).")

    def plan_by_id(self, plan_id: int | None) -> dict | None:
        return next((plan for plan in self.plans if plan.get("plan_id") == plan_id), None)

    def item_by_id(self, item_id: int | None) -> dict | None:
        return next((item for item in self.items if item.get("budget_item_id") == item_id), None)

    def default_payment_amount(self) -> None:
        plan = self.plan_by_id(current_combo_value(self.payment_plan))
        if plan:
            self.payment_amount.setValue(float(plan.get("semestral_fee_amount") or 0))

    def refresh_expense_items(self) -> None:
        plan_id = current_combo_value(self.expense_plan)
        bucket_ids = {
            bucket.get("bucket_id")
            for bucket in self.buckets
            if bucket.get("plan_id") == plan_id
        }
        rows = [item for item in self.items if item.get("bucket_id") in bucket_ids]
        set_combo_options(
            self.expense_item,
            rows,
            "budget_item_id",
            lambda row: f"#{row.get('budget_item_id')} {row.get('item_name')} - {money(row.get('planned_amount'))}",
            "Select budget item",
        )
        self.default_expense_amount()

    def default_expense_amount(self) -> None:
        item = self.item_by_id(current_combo_value(self.expense_item))
        if item:
            self.expense_amount.setValue(float(item.get("planned_amount") or 0))

    def sync_inventory_fields(self) -> None:
        enabled = self.capture_inventory.isChecked()
        for widget in [
            self.inventory_name,
            self.inventory_quantity,
            self.inventory_condition,
            self.inventory_status,
            self.inventory_date,
        ]:
            widget.setEnabled(enabled)

    def clear_payment_form(self) -> None:
        self.current_payment_id = None
        self.payment_id.clear()
        self.payment_date.setText(now_text())
        self.payment_notes.clear()
        self.payment_approval.setCurrentText("Pending")
        self.payment_status.setCurrentText("Active")
        self.default_payment_amount()
        self.set_status("Ready for a new payment.")

    def clear_expense_form(self) -> None:
        self.current_expense_id = None
        self.expense_id.clear()
        self.expense_date.setText(now_text())
        self.expense_receipt.clear()
        self.expense_notes.clear()
        self.expense_approval.setCurrentText("Pending")
        self.expense_status.setCurrentText("Active")
        self.capture_inventory.setChecked(False)
        self.inventory_name.clear()
        self.inventory_quantity.setValue(1)
        self.inventory_condition.setCurrentText("New")
        self.inventory_status.setCurrentText("Active")
        self.inventory_date.setText(today_text())
        self.default_expense_amount()
        self.sync_inventory_fields()
        self.set_status("Ready for a new expense.")

    def load_selected_transaction(self) -> None:
        row = self.table.selected_record()
        if not row:
            return
        if row.get("transaction_type") == "PAYMENT":
            self.current_payment_id = row.get("transaction_id")
            self.payment_id.setText(str(row.get("transaction_id") or ""))
            set_combo_value(self.payment_plan, row.get("plan_id"))
            set_combo_value(self.payment_student, row.get("student_id"))
            self.payment_amount.setValue(float(row.get("amount") or 0))
            set_combo_value(self.payment_approver, row.get("approver_id"))
            self.payment_approval.setCurrentText(row.get("approval_status") or "Pending")
            self.payment_status.setCurrentText(row.get("transaction_status") or "Active")
            self.payment_date.setText(row.get("transaction_date") or now_text())
            self.payment_notes.setPlainText(row.get("notes") or "")
            self.set_status(f"Loaded payment #{self.current_payment_id}.")
        else:
            self.current_expense_id = row.get("transaction_id")
            self.expense_id.setText(str(row.get("transaction_id") or ""))
            set_combo_value(self.expense_plan, row.get("plan_id"))
            self.refresh_expense_items()
            set_combo_value(self.expense_item, row.get("budget_item_id"))
            self.expense_amount.setValue(float(row.get("amount") or 0))
            set_combo_value(self.expense_approver, row.get("approver_id"))
            self.expense_approval.setCurrentText(row.get("approval_status") or "Pending")
            self.expense_status.setCurrentText(row.get("transaction_status") or "Active")
            self.expense_date.setText(row.get("transaction_date") or now_text())
            self.expense_receipt.setText(row.get("receipt_path") or "")
            self.expense_notes.setPlainText(row.get("notes") or "")
            self.capture_inventory.setChecked(False)
            self.sync_inventory_fields()
            self.set_status(f"Loaded expense #{self.current_expense_id}.")

    def save_payment(self) -> None:
        plan_id = current_combo_value(self.payment_plan)
        student_id = current_combo_value(self.payment_student)
        if not plan_id or not student_id:
            self.show_error("Payment save failed", "Select a budget plan and student.")
            return
        if self.payment_amount.value() <= 0:
            self.show_error("Payment save failed", "Payment amount must be greater than 0.")
            return

        payload = {
            "plan_id": plan_id,
            "student_id": student_id,
            "approver_id": current_combo_value(self.payment_approver),
            "amount": self.payment_amount.value(),
            "transaction_type": "PAYMENT",
            "transaction_status": self.payment_status.currentText().strip() or "Active",
            "approval_status": self.payment_approval.currentText().strip() or "Pending",
            "transaction_date": optional_text(self.payment_date),
            "notes": optional_text(self.payment_notes),
        }
        try:
            if self.current_payment_id:
                transaction = update_transaction(self.current_payment_id, payload)
                if not transaction:
                    raise ValueError("Payment was not found.")
                self.set_status(f"Updated payment #{self.current_payment_id}.")
            else:
                transaction = create_transaction(payload)
                self.current_payment_id = transaction["transaction_id"]
                self.set_status(f"Recorded payment #{self.current_payment_id}.")
        except Exception as exc:
            self.show_error("Payment save failed", exc)
            return

        self.refresh()
        self.table.select_record_by_key("transaction_id", self.current_payment_id)

    def save_expense(self) -> None:
        plan_id = current_combo_value(self.expense_plan)
        budget_item_id = current_combo_value(self.expense_item)
        if not plan_id or not budget_item_id:
            self.show_error("Expense save failed", "Select a budget plan and budget item.")
            return
        if self.expense_amount.value() <= 0:
            self.show_error("Expense save failed", "Expense amount must be greater than 0.")
            return
        if self.capture_inventory.isChecked() and not self.inventory_name.text().strip():
            self.show_error("Expense save failed", "Inventory name is required when inventory capture is enabled.")
            return

        payload = {
            "plan_id": plan_id,
            "budget_item_id": budget_item_id,
            "approver_id": current_combo_value(self.expense_approver),
            "amount": self.expense_amount.value(),
            "transaction_type": "EXPENSE",
            "transaction_status": self.expense_status.currentText().strip() or "Active",
            "approval_status": self.expense_approval.currentText().strip() or "Pending",
            "transaction_date": optional_text(self.expense_date),
            "receipt_path": optional_text(self.expense_receipt),
            "notes": optional_text(self.expense_notes),
        }
        try:
            if self.current_expense_id:
                transaction = update_transaction(self.current_expense_id, payload)
                if not transaction:
                    raise ValueError("Expense was not found.")
                transaction_id = self.current_expense_id
                message = f"Updated expense #{transaction_id}."
            else:
                transaction = create_transaction(payload)
                transaction_id = transaction["transaction_id"]
                self.current_expense_id = transaction_id
                message = f"Recorded expense #{transaction_id}."

            if self.capture_inventory.isChecked():
                create_inventory_item(
                    {
                        "transaction_id": transaction_id,
                        "item_name": self.inventory_name.text().strip(),
                        "quantity": self.inventory_quantity.value(),
                        "item_condition": self.inventory_condition.currentText().strip() or "New",
                        "status": self.inventory_status.currentText().strip() or "Active",
                        "date_recorded": optional_text(self.inventory_date),
                    }
                )
                message += " Inventory item recorded."
            self.set_status(message)
        except Exception as exc:
            self.show_error("Expense save failed", exc)
            return

        self.refresh()
        self.table.select_record_by_key("transaction_id", self.current_expense_id)

    def delete_selected_transaction(self) -> None:
        row = self.table.selected_record()
        if not row:
            self.show_error("Delete failed", "Select a transaction first.")
            return
        transaction_id = row.get("transaction_id")
        if not self.confirm("Delete Transaction", f"Delete transaction #{transaction_id}?"):
            return
        try:
            deleted = delete_transaction(transaction_id)
        except Exception as exc:
            self.show_error("Delete failed", exc)
            return
        if not deleted:
            self.show_error("Delete failed", "Transaction was not found.")
            return
        if transaction_id == self.current_payment_id:
            self.clear_payment_form()
        if transaction_id == self.current_expense_id:
            self.clear_expense_form()
        self.refresh()


class InventoryTab(WorkflowTab):
    def __init__(self) -> None:
        super().__init__()
        self.transactions: list[dict] = []
        self.items: list[dict] = []
        self.inventory: list[dict] = []
        self.current_inventory_id: int | None = None

        self.table = DataTable(
            [
                ("inventory_item_id", "ID"),
                ("transaction_id", "Expense Txn"),
                ("item_name", "Item"),
                ("quantity", "Qty"),
                ("item_condition", "Condition"),
                ("status", "Status"),
                ("date_recorded", "Date"),
            ],
            min_height=300,
        )
        self.table.itemSelectionChanged.connect(self.load_selected_inventory)

        self.inventory_id = QLineEdit()
        self.inventory_id.setReadOnly(True)
        self.transaction_combo = QComboBox()
        self.item_name = QLineEdit()
        self.quantity = make_quantity_input()
        self.condition = make_status_combo(("New", "Good", "Needs Repair", "Retired"), editable=True)
        self.status_combo = make_status_combo(("Active", "Archived"), editable=True)
        self.date_recorded = QLineEdit(today_text())

        form = QFormLayout()
        form.addRow("Inventory ID", self.inventory_id)
        form.addRow("Expense Transaction", self.transaction_combo)
        form.addRow("Item Name", self.item_name)
        form.addRow("Quantity", self.quantity)
        form.addRow("Condition", self.condition)
        form.addRow("Status", self.status_combo)
        form.addRow("Date Recorded", self.date_recorded)
        group = QGroupBox("Inventory Item")
        group.setLayout(form)

        save_button = QPushButton("Save Inventory Item")
        save_button.clicked.connect(self.save_inventory)
        new_button = QPushButton("New")
        new_button.clicked.connect(self.clear_form)
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_selected_inventory)
        buttons = QHBoxLayout()
        buttons.addWidget(save_button)
        buttons.addWidget(new_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.addWidget(QLabel("Inventory items are physical assets connected to expense transactions."))
        layout.addWidget(self.table)
        layout.addWidget(group)
        layout.addLayout(buttons)
        layout.addWidget(self.status)
        self.setLayout(make_scrollable_tab(layout))

    def refresh(self) -> None:
        try:
            self.transactions = list_transactions()
            self.items = list_budget_items()
            self.inventory = list_inventory_items()
        except Exception as exc:
            self.show_error("Inventory load failed", exc)
            return

        expense_rows = [
            transaction
            for transaction in self.transactions
            if transaction.get("transaction_type") == "EXPENSE"
        ]
        items_by_id = {item.get("budget_item_id"): item for item in self.items}
        set_combo_options(
            self.transaction_combo,
            expense_rows,
            "transaction_id",
            lambda row: (
                f"#{row.get('transaction_id')} "
                f"{items_by_id.get(row.get('budget_item_id'), {}).get('item_name', 'Expense')} "
                f"- {money(row.get('amount'))}"
            ),
            "Select expense transaction",
        )
        self.table.set_rows(self.inventory)
        self.set_status(f"Loaded {len(self.inventory)} inventory item(s).")

    def load_selected_inventory(self) -> None:
        row = self.table.selected_record()
        if not row:
            return
        self.current_inventory_id = row.get("inventory_item_id")
        self.inventory_id.setText(str(row.get("inventory_item_id") or ""))
        set_combo_value(self.transaction_combo, row.get("transaction_id"))
        self.item_name.setText(row.get("item_name") or "")
        self.quantity.setValue(int(row.get("quantity") or 1))
        self.condition.setCurrentText(row.get("item_condition") or "Good")
        self.status_combo.setCurrentText(row.get("status") or "Active")
        self.date_recorded.setText(row.get("date_recorded") or today_text())

    def clear_form(self) -> None:
        self.current_inventory_id = None
        self.table.clearSelection()
        self.inventory_id.clear()
        self.item_name.clear()
        self.quantity.setValue(1)
        self.condition.setCurrentText("New")
        self.status_combo.setCurrentText("Active")
        self.date_recorded.setText(today_text())
        self.set_status("Ready for a new inventory item.")

    def save_inventory(self) -> None:
        transaction_id = current_combo_value(self.transaction_combo)
        if not transaction_id:
            self.show_error("Inventory save failed", "Select an expense transaction.")
            return
        if not self.item_name.text().strip():
            self.show_error("Inventory save failed", "Item name is required.")
            return
        payload = {
            "transaction_id": transaction_id,
            "item_name": self.item_name.text().strip(),
            "quantity": self.quantity.value(),
            "item_condition": self.condition.currentText().strip() or "Good",
            "status": self.status_combo.currentText().strip() or "Active",
            "date_recorded": optional_text(self.date_recorded),
        }
        try:
            if self.current_inventory_id:
                item = update_inventory_item(self.current_inventory_id, payload)
                if not item:
                    raise ValueError("Inventory item was not found.")
                self.set_status(f"Updated inventory item #{self.current_inventory_id}.")
            else:
                item = create_inventory_item(payload)
                self.current_inventory_id = item["inventory_item_id"]
                self.set_status(f"Created inventory item #{self.current_inventory_id}.")
        except Exception as exc:
            self.show_error("Inventory save failed", exc)
            return
        self.refresh()
        self.table.select_record_by_key("inventory_item_id", self.current_inventory_id)

    def delete_selected_inventory(self) -> None:
        row = self.table.selected_record()
        if not row:
            self.show_error("Delete failed", "Select an inventory item first.")
            return
        inventory_id = row.get("inventory_item_id")
        if not self.confirm("Delete Inventory Item", f"Delete inventory item #{inventory_id}?"):
            return
        try:
            deleted = delete_inventory_item(inventory_id)
        except Exception as exc:
            self.show_error("Delete failed", exc)
            return
        if not deleted:
            self.show_error("Delete failed", "Inventory item was not found.")
            return
        self.clear_form()
        self.refresh()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GLASS Budget Manager")
        self.resize(1180, 820)

        self.tabs = QTabWidget()
        self.workflow_tabs: list[WorkflowTab] = [
            OverviewTab(),
            MembersTab(),
            BudgetPlanningTab(),
            TransactionsTab(),
            InventoryTab(),
        ]
        labels = [
            "Overview",
            "Members & Officers",
            "Budget Planning",
            "Transactions",
            "Inventory",
        ]
        for tab, label in zip(self.workflow_tabs, labels, strict=True):
            self.tabs.addTab(tab, label)

        self.tabs.currentChanged.connect(self.refresh_current_tab)
        self.setCentralWidget(self.tabs)
        self.refresh_all_tabs()

    def refresh_current_tab(self) -> None:
        current = self.tabs.currentWidget()
        if isinstance(current, WorkflowTab):
            current.refresh()

    def refresh_all_tabs(self) -> None:
        for tab in self.workflow_tabs:
            tab.refresh()


def main() -> None:
    init_db()
    app = QApplication(sys.argv)
    _apply_stylesheet(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def _apply_stylesheet(app: QApplication) -> None:
    style_path = Path(__file__).resolve().parent / "desktop" / "style.qss"
    if not style_path.exists():
        return
    app.setStyleSheet(style_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
