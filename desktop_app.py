from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
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
    QSplitter,
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
from services.dashboard_service import get_dashboard_summary
from services.inventory_service import (
    create_inventory_item,
    delete_inventory_item,
    list_inventory_items,
    update_inventory_item,
)
from services.report_service import REPORT_TYPES, generate_report_pdf, get_report_data
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
    if value is None or value == "":
        return "PHP 0.00"
    try:
        return f"PHP {float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def table_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def input_text(widget: QLineEdit) -> str:
    return widget.text().strip()


def optional_text(widget: QLineEdit | QTextEdit) -> str | None:
    if isinstance(widget, QTextEdit):
        value = widget.toPlainText().strip()
    else:
        value = widget.text().strip()
    return value or None


def today_text() -> str:
    return date.today().isoformat()


def now_text() -> str:
    return datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes")


def default_academic_year() -> str:
    today = date.today()
    start_year = today.year if today.month >= 6 else today.year - 1
    return f"{start_year}-{start_year + 1}"


def optional_money(spin: QDoubleSpinBox) -> float | None:
    value = float(spin.value())
    return value if value > 0 else None


def make_money_input(required: bool = True) -> QDoubleSpinBox:
    field = QDoubleSpinBox()
    field.setDecimals(2)
    field.setMaximum(999_999_999.99)
    field.setMinimum(0.01 if required else 0.0)
    field.setSingleStep(100.0)
    field.setPrefix("PHP ")
    return field


def make_quantity_input() -> QSpinBox:
    field = QSpinBox()
    field.setMinimum(1)
    field.setMaximum(999_999)
    return field


def make_combo(values: tuple[str, ...] | list[str], editable: bool = False) -> QComboBox:
    combo = QComboBox()
    combo.setEditable(editable)
    for value in values:
        combo.addItem(value, value)
    return combo


def current_combo_value(combo: QComboBox) -> Any:
    if combo.currentIndex() < 0:
        return None
    return combo.currentData()


def set_combo_value(combo: QComboBox, value: Any) -> bool:
    for index in range(combo.count()):
        item_value = combo.itemData(index)
        if item_value == value or str(item_value) == str(value):
            combo.setCurrentIndex(index)
            return True
    return False


def set_combo_options(
    combo: QComboBox,
    rows: list[dict],
    label_fn: Callable[[dict], str],
    value_key: str,
    *,
    include_blank: bool = False,
    blank_label: str = "Select",
    preferred_value: Any = None,
) -> None:
    current = current_combo_value(combo)
    target = preferred_value if preferred_value is not None else current
    combo.blockSignals(True)
    combo.clear()
    if include_blank:
        combo.addItem(blank_label, None)
    for row in rows:
        combo.addItem(label_fn(row), row.get(value_key))
    combo.blockSignals(False)
    if target is not None and set_combo_value(combo, target):
        return
    if combo.count() and combo.currentIndex() < 0:
        combo.setCurrentIndex(0)


def active_or_latest_plan(plans: list[dict]) -> dict | None:
    if not plans:
        return None
    active = [plan for plan in plans if plan.get("status") == "Active"]
    return max(active or plans, key=lambda plan: plan.get("plan_id") or 0)


def plan_label(plan: dict) -> str:
    return (
        f"#{plan.get('plan_id')} {plan.get('academic_year', '')} "
        f"{plan.get('semester', '')} ({plan.get('status', '')})"
    )


def student_label(student: dict) -> str:
    return f"{student.get('student_id', '')} - {student.get('name', '')}"


def bucket_label(bucket: dict) -> str:
    return f"#{bucket.get('bucket_id')} {bucket.get('bucket_name', '')}"


def item_label(item: dict) -> str:
    return f"#{item.get('budget_item_id')} {item.get('item_name', '')}"


def expense_label(transaction: dict) -> str:
    date_part = str(transaction.get("transaction_date") or "")[:10]
    return (
        f"#{transaction.get('transaction_id')} {date_part} "
        f"{money(transaction.get('amount'))}"
    )


def line_item_label(item: dict) -> str:
    return (
        f"#{item.get('line_item_id')} {item.get('item_name', '')} "
        f"x{item.get('quantity', 1)} @ {money(item.get('unit_cost'))}"
    )


def map_by(rows: list[dict], key: str) -> dict[Any, dict]:
    return {row.get(key): row for row in rows}


def make_scrollable(widget: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)
    return scroll


def group_box(title: str, layout: QVBoxLayout | QFormLayout) -> QGroupBox:
    group = QGroupBox(title)
    group.setLayout(layout)
    return group


class DataTable(QTableWidget):
    def __init__(self, columns: list[tuple[str, Callable[[dict], Any]]]) -> None:
        super().__init__(0, len(columns))
        self.columns = columns
        self.all_rows: list[dict] = []
        self.visible_rows: list[dict] = []
        self.filter_text = ""
        self.setHorizontalHeaderLabels([header for header, _ in columns])
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_rows(self, rows: list[dict]) -> None:
        self.all_rows = list(rows)
        self.apply_filter()

    def set_filter(self, text: str) -> None:
        self.filter_text = text.strip().lower()
        self.apply_filter()

    def apply_filter(self) -> None:
        if self.filter_text:
            self.visible_rows = [
                row
                for row in self.all_rows
                if self.filter_text
                in " ".join(table_text(value) for value in row.values()).lower()
            ]
        else:
            self.visible_rows = list(self.all_rows)

        self.setRowCount(len(self.visible_rows))
        for row_index, row in enumerate(self.visible_rows):
            for column_index, (_, value_fn) in enumerate(self.columns):
                raw = value_fn(row)
                item = QTableWidgetItem(table_text(raw))
                item.setData(Qt.ItemDataRole.UserRole, row)
                self.setItem(row_index, column_index, item)
        self.resizeColumnsToContents()

    def selected_record(self) -> dict | None:
        selected = self.selectedItems()
        if not selected:
            return None
        return selected[0].data(Qt.ItemDataRole.UserRole)

    def select_record_by_key(self, key: str, value: Any) -> None:
        for row_index, row in enumerate(self.visible_rows):
            row_value = row.get(key)
            if row_value == value or str(row_value) == str(value):
                self.selectRow(row_index)
                return


def table_search(table: DataTable, placeholder: str = "Search") -> QLineEdit:
    search = QLineEdit()
    search.setPlaceholderText(placeholder)
    search.textChanged.connect(table.set_filter)
    return search


class LineItemDialog(QDialog):
    def __init__(self, parent: QWidget, line_item: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Expense Line Item")
        self.item_name = QLineEdit()
        self.quantity = make_quantity_input()
        self.unit_cost = make_money_input()

        if line_item:
            self.item_name.setText(line_item.get("item_name") or "")
            self.quantity.setValue(int(line_item.get("quantity") or 1))
            self.unit_cost.setValue(float(line_item.get("unit_cost") or 0.01))

        form = QFormLayout()
        form.addRow("Item Name", self.item_name)
        form.addRow("Quantity", self.quantity)
        form.addRow("Unit Cost", self.unit_cost)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        if not input_text(self.item_name):
            QMessageBox.warning(self, "GLASS", "Line item name is required.")
            return
        super().accept()

    def payload(self) -> dict:
        return {
            "item_name": input_text(self.item_name),
            "quantity": self.quantity.value(),
            "unit_cost": self.unit_cost.value(),
            "line_total": self.quantity.value() * self.unit_cost.value(),
        }


class OverrideTotalDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        *,
        computed_total: float,
        remaining_budget: float | None,
        current_amount: float,
        reason: str | None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Override Expense Total")
        self.computed_total = float(computed_total)
        self.remaining_budget = remaining_budget
        self.amount = make_money_input()
        self.amount.setValue(max(float(current_amount or computed_total or 0.01), 0.01))
        self.reason = QLineEdit()
        self.reason.setText(reason or "")

        remaining_text = "No budget item selected"
        if remaining_budget is not None:
            remaining_text = money(remaining_budget)

        form = QFormLayout()
        form.addRow("Line Total", QLabel(money(computed_total)))
        form.addRow("Remaining Budget", QLabel(remaining_text))
        form.addRow("Ledger Amount", self.amount)
        form.addRow("Reason", self.reason)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def accept(self) -> None:
        amount = self.amount.value()
        if abs(amount - self.computed_total) > 0.009 and not input_text(self.reason):
            QMessageBox.warning(self, "GLASS", "Override reason is required.")
            return
        if self.remaining_budget is not None and amount > self.remaining_budget + 0.009:
            QMessageBox.warning(
                self,
                "GLASS",
                f"Ledger amount exceeds the remaining budget cap of {money(self.remaining_budget)}.",
            )
            return
        super().accept()

    def payload(self) -> tuple[bool, float, str | None]:
        amount = self.amount.value()
        if abs(amount - self.computed_total) <= 0.009:
            return False, amount, None
        return True, amount, input_text(self.reason)


class CashFlowChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict] = []
        self.setMinimumHeight(170)

    def set_rows(self, rows: list[dict]) -> None:
        self.rows = list(rows)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setPen(QPen(QColor("#c9d1db"), 1))
        painter.drawRect(rect)

        if not self.rows:
            painter.setPen(QColor("#657282"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No approved cash flow yet")
            return

        balances = [float(row.get("running_balance") or 0) for row in self.rows]
        low = min(min(balances), 0.0)
        high = max(max(balances), 0.0)
        if high == low:
            high += 1.0
            low -= 1.0

        def point(index: int, balance: float) -> QPointF:
            x = rect.left() + (rect.width() * index / max(len(balances) - 1, 1))
            y = rect.bottom() - ((balance - low) / (high - low) * rect.height())
            return QPointF(x, y)

        zero_y = point(0, 0.0).y()
        painter.setPen(QPen(QColor("#9aa6b2"), 1))
        painter.drawLine(rect.left(), int(zero_y), rect.right(), int(zero_y))

        painter.setPen(QPen(QColor("#2364aa"), 2))
        previous = point(0, balances[0])
        for index, balance in enumerate(balances[1:], start=1):
            current = point(index, balance)
            painter.drawLine(previous, current)
            previous = current

        painter.setBrush(QColor("#2364aa"))
        painter.setPen(Qt.PenStyle.NoPen)
        for index, balance in enumerate(balances):
            current = point(index, balance)
            painter.drawEllipse(current, 3, 3)


class AppTab(QWidget):
    def __init__(self, main: "MainWindow") -> None:
        super().__init__()
        self.main = main
        self.refreshing = False

    def refresh(self) -> None:
        return

    def show_error(self, error: Exception | str) -> None:
        QMessageBox.warning(self, "GLASS", str(error))

    def show_info(self, message: str) -> None:
        QMessageBox.information(self, "GLASS", message)

    def confirm(self, message: str) -> bool:
        return (
            QMessageBox.question(
                self,
                "GLASS",
                message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )


class DashboardTab(AppTab):
    def __init__(self, main: "MainWindow") -> None:
        super().__init__(main)
        self.plan_combo = QComboBox()
        self.plan_combo.currentIndexChanged.connect(self.load_summary)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)

        payment_button = QPushButton("Record Payment")
        payment_button.clicked.connect(self.main.open_payment_workflow)
        expense_button = QPushButton("Record Expense")
        expense_button.clicked.connect(self.main.open_expense_workflow)
        legacy_button = QPushButton("Add Legacy Inventory")
        legacy_button.clicked.connect(self.main.open_legacy_inventory_workflow)
        report_button = QPushButton("Generate Report")
        report_button.clicked.connect(self.main.open_reports_workflow)

        top = QHBoxLayout()
        top.addWidget(QLabel("Plan"))
        top.addWidget(self.plan_combo, 1)
        top.addWidget(refresh_button)
        top.addStretch()
        top.addWidget(payment_button)
        top.addWidget(expense_button)
        top.addWidget(legacy_button)
        top.addWidget(report_button)

        self.metrics: dict[str, QLabel] = {}
        metrics_layout = QHBoxLayout()
        for key, label in [
            ("plan", "Active Plan"),
            ("collections", "Collection"),
            ("cash", "Available Funds"),
            ("inventory", "Inventory"),
        ]:
            box_layout = QVBoxLayout()
            title = QLabel(label)
            value = QLabel("-")
            value.setWordWrap(True)
            value.setObjectName("metricValue")
            box_layout.addWidget(title)
            box_layout.addWidget(value)
            metrics_layout.addWidget(group_box("", box_layout), 1)
            self.metrics[key] = value

        self.chart = CashFlowChart()
        self.cash_table = DataTable(
            [
                ("Date", lambda row: str(row.get("transaction_date") or "")[:10]),
                ("Type", lambda row: row.get("transaction_type")),
                ("Amount", lambda row: money(row.get("amount"))),
                ("Balance", lambda row: money(row.get("running_balance"))),
            ]
        )
        cash_layout = QVBoxLayout()
        cash_layout.addWidget(self.chart)
        cash_layout.addWidget(self.cash_table)

        self.bucket_table = DataTable(
            [
                ("Bucket", lambda row: row.get("bucket_name")),
                ("Planned", lambda row: money(row.get("planned_amount"))),
                ("Spent", lambda row: money(row.get("spent_amount"))),
                ("Remaining", lambda row: money(row.get("remaining_amount"))),
            ]
        )
        self.item_table = DataTable(
            [
                ("Budget Item", lambda row: row.get("item_name")),
                ("Planned", lambda row: money(row.get("planned_amount"))),
                ("Spent", lambda row: money(row.get("spent_amount"))),
                ("Remaining", lambda row: money(row.get("remaining_amount"))),
                ("Status", lambda row: row.get("spending_status")),
            ]
        )
        self.inventory_table = DataTable(
            [
                ("Item", lambda row: row.get("item_name")),
                ("Source", lambda row: row.get("source_type")),
                ("Qty", lambda row: row.get("quantity")),
                ("Condition", lambda row: row.get("item_condition")),
                ("Txn", lambda row: row.get("transaction_id")),
            ]
        )

        grid = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(group_box("Cash Flow", cash_layout))
        right = QVBoxLayout()
        right.addWidget(group_box("Fund Buckets", self._table_layout(self.bucket_table)))
        right.addWidget(group_box("Budget Items", self._table_layout(self.item_table)))
        right.addWidget(group_box("Inventory", self._table_layout(self.inventory_table)))
        grid.addLayout(left, 2)
        grid.addLayout(right, 3)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(metrics_layout)
        layout.addLayout(grid, 1)

    def _table_layout(self, table: DataTable) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.addWidget(table)
        return layout

    def refresh(self) -> None:
        self.refreshing = True
        try:
            self.plans = list_budget_plans()
            active = active_or_latest_plan(self.plans)
            set_combo_options(
                self.plan_combo,
                self.plans,
                plan_label,
                "plan_id",
                preferred_value=active.get("plan_id") if active else None,
            )
        finally:
            self.refreshing = False
        self.load_summary()

    def load_summary(self, *_args) -> None:
        if self.refreshing:
            return
        try:
            plan_id = current_combo_value(self.plan_combo)
            summary = get_dashboard_summary(plan_id)
            plan = summary.get("active_plan")
            if not plan:
                self.metrics["plan"].setText("No budget plan yet")
                self.metrics["collections"].setText("0 paid, 0 pending")
                self.metrics["cash"].setText(money(0))
                self.metrics["inventory"].setText("0 recorded items")
                for table in [self.cash_table, self.bucket_table, self.item_table, self.inventory_table]:
                    table.set_rows([])
                self.chart.set_rows([])
                return

            collection = summary["collection_progress"]
            totals = summary["totals"]
            inventory = summary["inventory_summary"]
            self.metrics["plan"].setText(
                f"{plan['academic_year']} {plan['semester']} | Fee {money(plan['semestral_fee_amount'])}"
            )
            self.metrics["collections"].setText(
                f"{collection['paid_count']} paid, {collection['pending_count']} pending"
            )
            self.metrics["cash"].setText(
                f"{money(totals['available_funds'])} available\n"
                f"{money(totals['payments'])} in, {money(totals['expenses'])} out"
            )
            self.metrics["inventory"].setText(
                f"{inventory['total_items']} records, {inventory['total_quantity']} total qty"
            )
            self.cash_table.set_rows(summary["cash_flow"])
            self.chart.set_rows(summary["cash_flow"])
            self.bucket_table.set_rows(summary["fund_bucket_utilization"])
            self.item_table.set_rows(summary["budget_item_spending"])
            self.inventory_table.set_rows(inventory["items"])
        except Exception as error:
            self.show_error(error)


class MembersTab(AppTab):
    def __init__(self, main: "MainWindow") -> None:
        super().__init__(main)
        self.current_student_id: str | None = None
        self.students: list[dict] = []

        self.table = DataTable(
            [
                ("Student ID", lambda row: row.get("student_id")),
                ("Name", lambda row: row.get("name")),
                ("Program", lambda row: row.get("program")),
                ("Year", lambda row: row.get("year_level")),
                ("Role", lambda row: row.get("role_title")),
                ("Can Approve", lambda row: row.get("can_approve")),
                ("Status", lambda row: row.get("status")),
            ]
        )
        self.table.itemSelectionChanged.connect(self.load_selected)

        self.officers_only = QCheckBox("Officers only")
        self.officers_only.toggled.connect(self.refresh_member_table)

        left = QVBoxLayout()
        left.addWidget(table_search(self.table, "Search members"))
        left.addWidget(self.officers_only)
        left.addWidget(self.table)

        self.student_id = QLineEdit()
        self.student_id.setPlaceholderText("2026-0001")
        self.name = QLineEdit()
        self.program = QLineEdit()
        self.year_level = QSpinBox()
        self.year_level.setMinimum(1)
        self.year_level.setMaximum(6)
        self.role_title = QLineEdit()
        self.can_approve = QCheckBox("Can approve transactions")
        self.status = make_combo(["Active", "Inactive", "Alumni"])

        form = QFormLayout()
        form.addRow("Student ID", self.student_id)
        form.addRow("Name", self.name)
        form.addRow("Program", self.program)
        form.addRow("Year Level", self.year_level)
        form.addRow("Role", self.role_title)
        form.addRow("", self.can_approve)
        form.addRow("Status", self.status)

        new_button = QPushButton("New")
        new_button.clicked.connect(self.new_record)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_record)
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_record)
        buttons = QHBoxLayout()
        buttons.addWidget(new_button)
        buttons.addWidget(save_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        right = QVBoxLayout()
        right.addWidget(group_box("Member Details", form))
        right.addLayout(buttons)
        right.addStretch()

        splitter = QSplitter()
        left_widget = QWidget()
        left_widget.setLayout(left)
        right_widget = QWidget()
        right_widget.setLayout(right)
        splitter.addWidget(left_widget)
        splitter.addWidget(make_scrollable(right_widget))
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

    def refresh(self) -> None:
        selected = self.current_student_id
        self.students = list_students()
        self.refresh_member_table()
        if selected:
            self.table.select_record_by_key("student_id", selected)

    def refresh_member_table(self, *_args) -> None:
        rows = self.students
        if self.officers_only.isChecked():
            rows = [student for student in rows if self.is_officer(student)]
        self.table.set_rows(rows)

    def is_officer(self, student: dict) -> bool:
        return bool((student.get("role_title") or "").strip()) or bool(student.get("can_approve"))

    def new_record(self) -> None:
        self.current_student_id = None
        self.student_id.setEnabled(True)
        self.student_id.clear()
        self.name.clear()
        self.program.clear()
        self.year_level.setValue(1)
        self.role_title.clear()
        self.can_approve.setChecked(False)
        set_combo_value(self.status, "Active")
        self.student_id.setFocus()

    def load_selected(self) -> None:
        record = self.table.selected_record()
        if not record:
            return
        self.current_student_id = record.get("student_id")
        self.student_id.setText(record.get("student_id") or "")
        self.student_id.setEnabled(False)
        self.name.setText(record.get("name") or "")
        self.program.setText(record.get("program") or "")
        self.year_level.setValue(int(record.get("year_level") or 1))
        self.role_title.setText(record.get("role_title") or "")
        self.can_approve.setChecked(bool(record.get("can_approve")))
        set_combo_value(self.status, record.get("status") or "Active")

    def payload(self) -> dict:
        return {
            "student_id": input_text(self.student_id),
            "name": input_text(self.name),
            "program": optional_text(self.program),
            "year_level": self.year_level.value(),
            "role_title": optional_text(self.role_title),
            "can_approve": self.can_approve.isChecked(),
            "status": current_combo_value(self.status),
        }

    def save_record(self) -> None:
        try:
            if self.current_student_id:
                result = update_student(self.current_student_id, self.payload())
                if not result:
                    raise ValueError("Selected member no longer exists")
            else:
                result = create_student(self.payload())
            self.current_student_id = result["student_id"]
            self.main.refresh_all()
            self.table.select_record_by_key("student_id", self.current_student_id)
            self.show_info("Member saved.")
        except Exception as error:
            self.show_error(error)

    def delete_record(self) -> None:
        if not self.current_student_id:
            self.show_error("Select a member first.")
            return
        if not self.confirm(f"Delete member {self.current_student_id}?"):
            return
        try:
            delete_student(self.current_student_id)
            self.current_student_id = None
            self.new_record()
            self.main.refresh_all()
        except Exception as error:
            self.show_error(error)


class BudgetTab(AppTab):
    def __init__(self, main: "MainWindow") -> None:
        super().__init__(main)
        self.plans: list[dict] = []
        self.students: list[dict] = []
        self.buckets: list[dict] = []
        self.items: list[dict] = []
        self.current_plan_id: int | None = None
        self.current_bucket_id: int | None = None
        self.current_item_id: int | None = None

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_plan_tab(), "Plan")
        self.tabs.addTab(self.build_bucket_tab(), "Fund Buckets")
        self.tabs.addTab(self.build_item_tab(), "Budget Items")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def build_plan_tab(self) -> QWidget:
        self.plan_table = DataTable(
            [
                ("ID", lambda row: row.get("plan_id")),
                ("Academic Year", lambda row: row.get("academic_year")),
                ("Semester", lambda row: row.get("semester")),
                ("Budget", lambda row: money(row.get("total_planned_budget"))),
                ("Fee", lambda row: money(row.get("semestral_fee_amount"))),
                ("Members", lambda row: row.get("member_count")),
                ("Approval", lambda row: row.get("approval_status")),
                ("Status", lambda row: row.get("status")),
            ]
        )
        self.plan_table.itemSelectionChanged.connect(self.load_selected_plan)
        left = QVBoxLayout()
        left.addWidget(table_search(self.plan_table, "Search plans"))
        left.addWidget(self.plan_table)

        self.plan_year = QLineEdit()
        self.plan_year.setPlaceholderText("2026-2027")
        self.plan_semester = make_combo(["1st", "2nd", "Midyear"])
        self.plan_total = make_money_input()
        self.plan_total.valueChanged.connect(self.update_fee_preview)
        self.plan_members = QListWidget()
        self.plan_members.itemChanged.connect(self.update_fee_preview)
        self.plan_fee = QLabel(money(0))
        self.plan_approval = make_combo(["Pending", "Approved", "Rejected"])
        self.plan_approved_date = QLineEdit()
        self.plan_approved_date.setPlaceholderText("YYYY-MM-DD")
        self.plan_status = make_combo(["Active", "Archived"])

        form = QFormLayout()
        form.addRow("Academic Year", self.plan_year)
        form.addRow("Semester", self.plan_semester)
        form.addRow("Total Planned Budget", self.plan_total)
        form.addRow("Master List", self.plan_members)
        form.addRow("Computed Fee", self.plan_fee)
        form.addRow("Approval", self.plan_approval)
        form.addRow("Approved Date", self.plan_approved_date)
        form.addRow("Status", self.plan_status)

        new_button = QPushButton("New Plan")
        new_button.clicked.connect(self.new_plan)
        save_button = QPushButton("Save Plan")
        save_button.clicked.connect(self.save_plan)
        delete_button = QPushButton("Delete Plan")
        delete_button.clicked.connect(self.delete_plan)
        buttons = QHBoxLayout()
        buttons.addWidget(new_button)
        buttons.addWidget(save_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        right = QVBoxLayout()
        right.addWidget(group_box("Plan Details", form))
        right.addLayout(buttons)
        right.addStretch()

        return self.two_pane(left, right)

    def build_bucket_tab(self) -> QWidget:
        self.bucket_plan_combo = QComboBox()
        self.bucket_plan_combo.currentIndexChanged.connect(self.refresh_bucket_area)
        self.bucket_table = DataTable(
            [
                ("ID", lambda row: row.get("bucket_id")),
                ("Bucket", lambda row: row.get("bucket_name")),
                ("Planned", lambda row: money(row.get("planned_amount"))),
                ("Description", lambda row: row.get("description")),
            ]
        )
        self.bucket_table.itemSelectionChanged.connect(self.load_selected_bucket)

        left = QVBoxLayout()
        selector = QHBoxLayout()
        selector.addWidget(QLabel("Plan"))
        selector.addWidget(self.bucket_plan_combo, 1)
        left.addLayout(selector)
        left.addWidget(table_search(self.bucket_table, "Search buckets"))
        left.addWidget(self.bucket_table)

        self.bucket_name = QLineEdit()
        self.bucket_amount = make_money_input()
        self.bucket_description = QTextEdit()
        self.bucket_description.setMaximumHeight(90)

        form = QFormLayout()
        form.addRow("Bucket Name", self.bucket_name)
        form.addRow("Planned Amount", self.bucket_amount)
        form.addRow("Description", self.bucket_description)

        new_button = QPushButton("New Bucket")
        new_button.clicked.connect(self.new_bucket)
        save_button = QPushButton("Save Bucket")
        save_button.clicked.connect(self.save_bucket)
        delete_button = QPushButton("Delete Bucket")
        delete_button.clicked.connect(self.delete_bucket)
        buttons = QHBoxLayout()
        buttons.addWidget(new_button)
        buttons.addWidget(save_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        right = QVBoxLayout()
        right.addWidget(group_box("Bucket Details", form))
        right.addLayout(buttons)
        right.addStretch()

        return self.two_pane(left, right)

    def build_item_tab(self) -> QWidget:
        self.item_plan_combo = QComboBox()
        self.item_plan_combo.currentIndexChanged.connect(self.refresh_item_bucket_options)
        self.item_bucket_combo = QComboBox()
        self.item_bucket_combo.currentIndexChanged.connect(self.refresh_item_area)
        self.item_table = DataTable(
            [
                ("ID", lambda row: row.get("budget_item_id")),
                ("Item", lambda row: row.get("item_name")),
                ("Type", lambda row: row.get("item_type")),
                ("Planned", lambda row: money(row.get("planned_amount"))),
                ("Description", lambda row: row.get("description")),
            ]
        )
        self.item_table.itemSelectionChanged.connect(self.load_selected_item)

        left = QVBoxLayout()
        selector = QHBoxLayout()
        selector.addWidget(QLabel("Plan"))
        selector.addWidget(self.item_plan_combo, 1)
        selector.addWidget(QLabel("Bucket"))
        selector.addWidget(self.item_bucket_combo, 1)
        left.addLayout(selector)
        left.addWidget(table_search(self.item_table, "Search budget items"))
        left.addWidget(self.item_table)

        self.item_name = QLineEdit()
        self.item_type = QLineEdit()
        self.item_amount = make_money_input()
        self.item_description = QTextEdit()
        self.item_description.setMaximumHeight(90)

        form = QFormLayout()
        form.addRow("Item Name", self.item_name)
        form.addRow("Type", self.item_type)
        form.addRow("Planned Amount", self.item_amount)
        form.addRow("Description", self.item_description)

        new_button = QPushButton("New Item")
        new_button.clicked.connect(self.new_item)
        save_button = QPushButton("Save Item")
        save_button.clicked.connect(self.save_item)
        delete_button = QPushButton("Delete Item")
        delete_button.clicked.connect(self.delete_item)
        buttons = QHBoxLayout()
        buttons.addWidget(new_button)
        buttons.addWidget(save_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        right = QVBoxLayout()
        right.addWidget(group_box("Budget Item Details", form))
        right.addLayout(buttons)
        right.addStretch()

        return self.two_pane(left, right)

    def two_pane(self, left: QVBoxLayout, right: QVBoxLayout) -> QWidget:
        splitter = QSplitter()
        left_widget = QWidget()
        left_widget.setLayout(left)
        right_widget = QWidget()
        right_widget.setLayout(right)
        splitter.addWidget(left_widget)
        splitter.addWidget(make_scrollable(right_widget))
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout()
        outer.addWidget(splitter)
        widget = QWidget()
        widget.setLayout(outer)
        return widget

    def refresh(self) -> None:
        self.refreshing = True
        try:
            selected_plan = self.current_plan_id
            selected_bucket = self.current_bucket_id
            selected_item = self.current_item_id
            self.students = list_students()
            self.plans = list_budget_plans()
            self.buckets = list_fund_buckets()
            self.items = list_budget_items()
            active = active_or_latest_plan(self.plans)
            default_plan_id = selected_plan or (active.get("plan_id") if active else None)

            self.plan_table.set_rows(self.plans)
            self.rebuild_member_list([])
            for combo in [self.bucket_plan_combo, self.item_plan_combo]:
                set_combo_options(
                    combo,
                    self.plans,
                    plan_label,
                    "plan_id",
                    preferred_value=default_plan_id,
                )
        finally:
            self.refreshing = False

        if default_plan_id:
            self.current_plan_id = default_plan_id
            self.plan_table.select_record_by_key("plan_id", default_plan_id)
            plan = map_by(self.plans, "plan_id").get(default_plan_id)
            if plan:
                self.load_plan(plan)
        else:
            self.new_plan()
        self.refresh_bucket_area()
        if selected_bucket:
            self.bucket_table.select_record_by_key("bucket_id", selected_bucket)
        self.refresh_item_bucket_options()
        if selected_item:
            self.item_table.select_record_by_key("budget_item_id", selected_item)

    def rebuild_member_list(self, selected_ids: list[str]) -> None:
        selected = set(selected_ids)
        self.plan_members.blockSignals(True)
        self.plan_members.clear()
        for student in self.students:
            item = QListWidgetItem(student_label(student))
            item.setData(Qt.ItemDataRole.UserRole, student.get("student_id"))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if student.get("student_id") in selected
                else Qt.CheckState.Unchecked
            )
            self.plan_members.addItem(item)
        self.plan_members.blockSignals(False)
        self.update_fee_preview()

    def selected_member_ids(self) -> list[str]:
        ids: list[str] = []
        for index in range(self.plan_members.count()):
            item = self.plan_members.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    def update_fee_preview(self, *_args) -> None:
        member_count = len(self.selected_member_ids())
        if member_count:
            fee = self.plan_total.value() / member_count
            self.plan_fee.setText(f"{money(fee)} ({member_count} member/s)")
        else:
            self.plan_fee.setText("Select members to compute fee")

    def new_plan(self) -> None:
        self.current_plan_id = None
        self.plan_year.setText(default_academic_year())
        set_combo_value(self.plan_semester, "1st")
        self.plan_total.setValue(0.01)
        self.rebuild_member_list([])
        set_combo_value(self.plan_approval, "Pending")
        self.plan_approved_date.clear()
        set_combo_value(self.plan_status, "Active")

    def load_selected_plan(self) -> None:
        record = self.plan_table.selected_record()
        if record:
            self.load_plan(record)
            set_combo_value(self.bucket_plan_combo, record.get("plan_id"))
            set_combo_value(self.item_plan_combo, record.get("plan_id"))
            self.refresh_bucket_area()
            self.refresh_item_bucket_options()

    def load_plan(self, record: dict) -> None:
        self.current_plan_id = record.get("plan_id")
        self.plan_year.setText(record.get("academic_year") or "")
        set_combo_value(self.plan_semester, record.get("semester") or "1st")
        self.plan_total.setValue(float(record.get("total_planned_budget") or 0.01))
        self.rebuild_member_list(record.get("student_ids") or [])
        set_combo_value(self.plan_approval, record.get("approval_status") or "Pending")
        self.plan_approved_date.setText(record.get("approved_date") or "")
        set_combo_value(self.plan_status, record.get("status") or "Active")

    def plan_payload(self) -> dict:
        member_ids = self.selected_member_ids()
        if not member_ids:
            raise ValueError("Select at least one member for the plan master list.")
        return {
            "academic_year": input_text(self.plan_year),
            "semester": current_combo_value(self.plan_semester),
            "total_planned_budget": self.plan_total.value(),
            "member_count": len(member_ids),
            "approval_status": current_combo_value(self.plan_approval),
            "approved_date": optional_text(self.plan_approved_date),
            "status": current_combo_value(self.plan_status),
            "student_ids": member_ids,
        }

    def save_plan(self) -> None:
        try:
            if self.current_plan_id:
                result = update_budget_plan(self.current_plan_id, self.plan_payload())
                if not result:
                    raise ValueError("Selected budget plan no longer exists")
            else:
                result = create_budget_plan(self.plan_payload())
            self.current_plan_id = result["plan_id"]
            self.main.refresh_all()
            self.plan_table.select_record_by_key("plan_id", self.current_plan_id)
            self.show_info("Budget plan saved.")
        except Exception as error:
            self.show_error(error)

    def delete_plan(self) -> None:
        if not self.current_plan_id:
            self.show_error("Select a budget plan first.")
            return
        if not self.confirm(f"Delete budget plan #{self.current_plan_id}?"):
            return
        try:
            delete_budget_plan(self.current_plan_id)
            self.current_plan_id = None
            self.main.refresh_all()
        except Exception as error:
            self.show_error(error)

    def refresh_bucket_area(self, *_args) -> None:
        if self.refreshing:
            return
        plan_id = current_combo_value(self.bucket_plan_combo)
        rows = [bucket for bucket in self.buckets if bucket.get("plan_id") == plan_id]
        self.bucket_table.set_rows(rows)
        if self.current_bucket_id:
            self.bucket_table.select_record_by_key("bucket_id", self.current_bucket_id)
        else:
            self.new_bucket()

    def new_bucket(self) -> None:
        self.current_bucket_id = None
        self.bucket_name.clear()
        self.bucket_amount.setValue(0.01)
        self.bucket_description.clear()

    def load_selected_bucket(self) -> None:
        record = self.bucket_table.selected_record()
        if record:
            self.load_bucket(record)

    def load_bucket(self, record: dict) -> None:
        self.current_bucket_id = record.get("bucket_id")
        set_combo_value(self.bucket_plan_combo, record.get("plan_id"))
        self.bucket_name.setText(record.get("bucket_name") or "")
        self.bucket_amount.setValue(float(record.get("planned_amount") or 0.01))
        self.bucket_description.setPlainText(record.get("description") or "")

    def save_bucket(self) -> None:
        try:
            plan_id = current_combo_value(self.bucket_plan_combo)
            if not plan_id:
                raise ValueError("Select a budget plan first.")
            payload = {
                "bucket_name": input_text(self.bucket_name),
                "planned_amount": self.bucket_amount.value(),
                "description": optional_text(self.bucket_description),
            }
            if self.current_bucket_id:
                result = update_fund_bucket(self.current_bucket_id, payload)
                if not result:
                    raise ValueError("Selected fund bucket no longer exists")
            else:
                result = create_fund_bucket({**payload, "plan_id": plan_id})
            self.current_bucket_id = result["bucket_id"]
            self.main.refresh_all()
            self.tabs.setCurrentIndex(1)
            self.bucket_table.select_record_by_key("bucket_id", self.current_bucket_id)
            self.show_info("Fund bucket saved.")
        except Exception as error:
            self.show_error(error)

    def delete_bucket(self) -> None:
        if not self.current_bucket_id:
            self.show_error("Select a fund bucket first.")
            return
        if not self.confirm(f"Delete fund bucket #{self.current_bucket_id}?"):
            return
        try:
            delete_fund_bucket(self.current_bucket_id)
            self.current_bucket_id = None
            self.main.refresh_all()
        except Exception as error:
            self.show_error(error)

    def refresh_item_bucket_options(self, *_args) -> None:
        if self.refreshing:
            return
        plan_id = current_combo_value(self.item_plan_combo)
        buckets = [bucket for bucket in self.buckets if bucket.get("plan_id") == plan_id]
        set_combo_options(
            self.item_bucket_combo,
            buckets,
            bucket_label,
            "bucket_id",
            preferred_value=self.current_bucket_id,
        )
        self.refresh_item_area()

    def refresh_item_area(self, *_args) -> None:
        if self.refreshing:
            return
        bucket_id = current_combo_value(self.item_bucket_combo)
        rows = [item for item in self.items if item.get("bucket_id") == bucket_id]
        self.item_table.set_rows(rows)
        if self.current_item_id:
            self.item_table.select_record_by_key("budget_item_id", self.current_item_id)
        else:
            self.new_item()

    def new_item(self) -> None:
        self.current_item_id = None
        self.item_name.clear()
        self.item_type.clear()
        self.item_amount.setValue(0.01)
        self.item_description.clear()

    def load_selected_item(self) -> None:
        record = self.item_table.selected_record()
        if record:
            self.load_item(record)

    def load_item(self, record: dict) -> None:
        self.current_item_id = record.get("budget_item_id")
        bucket = map_by(self.buckets, "bucket_id").get(record.get("bucket_id"))
        if bucket:
            set_combo_value(self.item_plan_combo, bucket.get("plan_id"))
            self.refresh_item_bucket_options()
        set_combo_value(self.item_bucket_combo, record.get("bucket_id"))
        self.item_name.setText(record.get("item_name") or "")
        self.item_type.setText(record.get("item_type") or "")
        self.item_amount.setValue(float(record.get("planned_amount") or 0.01))
        self.item_description.setPlainText(record.get("description") or "")

    def save_item(self) -> None:
        try:
            bucket_id = current_combo_value(self.item_bucket_combo)
            if not bucket_id:
                raise ValueError("Select a fund bucket first.")
            payload = {
                "item_name": input_text(self.item_name),
                "item_type": optional_text(self.item_type),
                "planned_amount": self.item_amount.value(),
                "description": optional_text(self.item_description),
            }
            if self.current_item_id:
                result = update_budget_item(self.current_item_id, payload)
                if not result:
                    raise ValueError("Selected budget item no longer exists")
            else:
                result = create_budget_item({**payload, "bucket_id": bucket_id})
            self.current_item_id = result["budget_item_id"]
            self.current_bucket_id = result["bucket_id"]
            self.main.refresh_all()
            self.tabs.setCurrentIndex(2)
            self.item_table.select_record_by_key("budget_item_id", self.current_item_id)
            self.show_info("Budget item saved.")
        except Exception as error:
            self.show_error(error)

    def delete_item(self) -> None:
        if not self.current_item_id:
            self.show_error("Select a budget item first.")
            return
        if not self.confirm(f"Delete budget item #{self.current_item_id}?"):
            return
        try:
            delete_budget_item(self.current_item_id)
            self.current_item_id = None
            self.main.refresh_all()
        except Exception as error:
            self.show_error(error)


class TransactionsTab(AppTab):
    def __init__(self, main: "MainWindow") -> None:
        super().__init__(main)
        self.plans: list[dict] = []
        self.students: list[dict] = []
        self.buckets: list[dict] = []
        self.items: list[dict] = []
        self.transactions: list[dict] = []
        self.current_payment_id: int | None = None
        self.current_expense_id: int | None = None
        self.expense_line_items: list[dict] = []
        self.editing_line_index: int | None = None
        self.override_enabled = False
        self.override_amount_value: float | None = None
        self.override_reason_value: str | None = None

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_payment_tab(), "Payments")
        self.tabs.addTab(self.build_expense_tab(), "Expenses")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def build_payment_tab(self) -> QWidget:
        self.payment_plan_combo = QComboBox()
        self.payment_plan_combo.currentIndexChanged.connect(self.refresh_payment_students)
        self.payment_table = DataTable(
            [
                ("ID", lambda row: row.get("transaction_id")),
                ("Date", lambda row: str(row.get("transaction_date") or "")[:10]),
                ("Student", lambda row: self.student_name(row.get("student_id"))),
                ("Amount", lambda row: money(row.get("amount"))),
                ("Approval", lambda row: row.get("approval_status")),
                ("Status", lambda row: row.get("transaction_status")),
            ]
        )
        self.payment_table.itemSelectionChanged.connect(self.load_selected_payment)

        left = QVBoxLayout()
        selector = QHBoxLayout()
        selector.addWidget(QLabel("Plan"))
        selector.addWidget(self.payment_plan_combo, 1)
        left.addLayout(selector)
        left.addWidget(table_search(self.payment_table, "Search payments"))
        left.addWidget(self.payment_table)

        self.payment_student_combo = QComboBox()
        self.payment_student_combo.currentIndexChanged.connect(self.default_payment_amount)
        self.payment_amount = make_money_input()
        self.payment_date = QLineEdit(now_text())
        self.payment_approval = make_combo(["Pending", "Approved", "Rejected"])
        self.payment_approver = QComboBox()
        self.payment_status = make_combo(["Active", "Void"])
        self.payment_receipt = QLineEdit()
        self.payment_notes = QTextEdit()
        self.payment_notes.setMaximumHeight(90)

        receipt_row = QHBoxLayout()
        receipt_row.addWidget(self.payment_receipt, 1)
        browse = QPushButton("Browse")
        browse.clicked.connect(lambda: self.choose_receipt(self.payment_receipt))
        receipt_row.addWidget(browse)
        receipt_widget = QWidget()
        receipt_widget.setLayout(receipt_row)

        form = QFormLayout()
        form.addRow("Student", self.payment_student_combo)
        form.addRow("Amount", self.payment_amount)
        form.addRow("Date/Time", self.payment_date)
        form.addRow("Approval", self.payment_approval)
        form.addRow("Approved By", self.payment_approver)
        form.addRow("Status", self.payment_status)
        form.addRow("Receipt Path", receipt_widget)
        form.addRow("Notes", self.payment_notes)

        new_button = QPushButton("New Payment")
        new_button.clicked.connect(self.new_payment)
        save_button = QPushButton("Save Payment")
        save_button.clicked.connect(self.save_payment)
        delete_button = QPushButton("Delete Payment")
        delete_button.clicked.connect(self.delete_payment)
        buttons = QHBoxLayout()
        buttons.addWidget(new_button)
        buttons.addWidget(save_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        right = QVBoxLayout()
        right.addWidget(group_box("Payment Details", form))
        right.addLayout(buttons)
        right.addStretch()
        return self.two_pane(left, right)

    def build_expense_tab(self) -> QWidget:
        self.expense_plan_combo = QComboBox()
        self.expense_plan_combo.currentIndexChanged.connect(self.refresh_expense_buckets)
        self.expense_bucket_combo = QComboBox()
        self.expense_bucket_combo.currentIndexChanged.connect(self.refresh_expense_items)
        self.expense_item_combo = QComboBox()
        self.expense_item_combo.currentIndexChanged.connect(self.update_line_totals)

        self.expense_table = DataTable(
            [
                ("ID", lambda row: row.get("transaction_id")),
                ("Date", lambda row: str(row.get("transaction_date") or "")[:10]),
                ("Bucket", lambda row: self.bucket_name_for_item(row.get("budget_item_id"))),
                ("Budget Item", lambda row: self.item_name(row.get("budget_item_id"))),
                ("Line Items", lambda row: self.line_summary(row)),
                ("Amount", lambda row: money(row.get("amount"))),
                ("Approval", lambda row: row.get("approval_status")),
                ("Status", lambda row: row.get("transaction_status")),
            ]
        )
        self.expense_table.itemSelectionChanged.connect(self.load_selected_expense)

        left = QVBoxLayout()
        selector = QHBoxLayout()
        selector.addWidget(QLabel("Plan"))
        selector.addWidget(self.expense_plan_combo, 1)
        left.addLayout(selector)
        left.addWidget(table_search(self.expense_table, "Search expenses"))
        left.addWidget(self.expense_table)

        hierarchy = QHBoxLayout()
        hierarchy.addWidget(QLabel("Bucket"))
        hierarchy.addWidget(self.expense_bucket_combo, 1)
        hierarchy.addWidget(QLabel("Budget Item"))
        hierarchy.addWidget(self.expense_item_combo, 1)

        add_line = QPushButton("Add Line")
        add_line.clicked.connect(self.add_line_item)
        edit_line = QPushButton("Edit Line")
        edit_line.clicked.connect(self.edit_line_item)
        remove_line = QPushButton("Remove Line")
        remove_line.clicked.connect(self.remove_line_item)

        line_buttons = QHBoxLayout()
        line_buttons.addWidget(add_line)
        line_buttons.addWidget(edit_line)
        line_buttons.addWidget(remove_line)
        line_buttons.addStretch()

        self.line_table = DataTable(
            [
                ("Item", lambda row: row.get("item_name")),
                ("Qty", lambda row: row.get("quantity")),
                ("Unit Cost", lambda row: money(row.get("unit_cost"))),
                ("Subtotal", lambda row: money(row.get("line_total"))),
            ]
        )
        self.line_table.itemSelectionChanged.connect(self.load_selected_line_item)
        self.computed_total = QLabel(money(0))
        self.ledger_total = QLabel(money(0))
        self.override_summary = QLabel("No override")
        self.budget_cap_label = QLabel(money(0))
        self.budget_reserved_label = QLabel(money(0))
        self.budget_remaining_label = QLabel(money(0))
        override_button = QPushButton("Override Total...")
        override_button.clicked.connect(self.open_override_dialog)
        clear_override = QPushButton("Clear Override")
        clear_override.clicked.connect(self.clear_total_override)

        override_buttons = QHBoxLayout()
        override_buttons.addWidget(override_button)
        override_buttons.addWidget(clear_override)
        override_buttons.addStretch()
        override_widget = QWidget()
        override_widget.setLayout(override_buttons)

        total_form = QFormLayout()
        total_form.addRow("Line Total", self.computed_total)
        total_form.addRow("Ledger Amount", self.ledger_total)
        total_form.addRow("Override", self.override_summary)
        total_form.addRow("", override_widget)
        total_form.addRow("Budget Item Cap", self.budget_cap_label)
        total_form.addRow("Reserved", self.budget_reserved_label)
        total_form.addRow("Remaining", self.budget_remaining_label)

        self.expense_date = QLineEdit(now_text())
        self.expense_approval = make_combo(["Pending", "Approved", "Rejected"])
        self.expense_approver = QComboBox()
        self.expense_status = make_combo(["Active", "Void"])
        self.expense_approval.currentIndexChanged.connect(self.update_line_totals)
        self.expense_status.currentIndexChanged.connect(self.update_line_totals)
        self.expense_receipt = QLineEdit()
        self.expense_notes = QTextEdit()
        self.expense_notes.setMaximumHeight(90)

        receipt_row = QHBoxLayout()
        receipt_row.addWidget(self.expense_receipt, 1)
        browse = QPushButton("Browse")
        browse.clicked.connect(lambda: self.choose_receipt(self.expense_receipt))
        receipt_row.addWidget(browse)
        receipt_widget = QWidget()
        receipt_widget.setLayout(receipt_row)

        tx_form = QFormLayout()
        tx_form.addRow("Date/Time", self.expense_date)
        tx_form.addRow("Approval", self.expense_approval)
        tx_form.addRow("Approved By", self.expense_approver)
        tx_form.addRow("Status", self.expense_status)
        tx_form.addRow("Receipt Path", receipt_widget)
        tx_form.addRow("Notes", self.expense_notes)

        self.capture_inventory = QCheckBox("Also record purchased inventory")
        self.capture_inventory.toggled.connect(self.sync_inventory_capture)
        self.purchase_item_name = QLineEdit()
        self.purchase_qty = make_quantity_input()
        self.purchase_unit_cost = make_money_input(required=False)
        self.purchase_condition = make_combo(["", "New", "Good", "Needs Repair", "Retired"])
        self.purchase_status = make_combo(["Active", "Archived"])
        self.purchase_inventory_box = QGroupBox("Purchased Inventory")
        inv_form = QFormLayout()
        inv_form.addRow("Item Name", self.purchase_item_name)
        inv_form.addRow("Quantity", self.purchase_qty)
        inv_form.addRow("Unit Cost", self.purchase_unit_cost)
        inv_form.addRow("Condition", self.purchase_condition)
        inv_form.addRow("Status", self.purchase_status)
        self.purchase_inventory_box.setLayout(inv_form)

        new_button = QPushButton("New Expense")
        new_button.clicked.connect(self.new_expense)
        save_button = QPushButton("Save Expense")
        save_button.clicked.connect(self.save_expense)
        delete_button = QPushButton("Delete Expense")
        delete_button.clicked.connect(self.delete_expense)
        buttons = QHBoxLayout()
        buttons.addWidget(new_button)
        buttons.addWidget(save_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        right = QVBoxLayout()
        right.addLayout(hierarchy)
        right.addLayout(line_buttons)
        right.addWidget(self.line_table)
        right.addWidget(group_box("Totals", total_form))
        right.addWidget(group_box("Approval and Receipt", tx_form))
        right.addWidget(self.capture_inventory)
        right.addWidget(self.purchase_inventory_box)
        right.addLayout(buttons)
        right.addStretch()
        self.sync_inventory_capture()
        return self.two_pane(left, right)

    def two_pane(self, left: QVBoxLayout, right: QVBoxLayout) -> QWidget:
        splitter = QSplitter()
        left_widget = QWidget()
        left_widget.setLayout(left)
        right_widget = QWidget()
        right_widget.setLayout(right)
        splitter.addWidget(left_widget)
        splitter.addWidget(make_scrollable(right_widget))
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout()
        outer.addWidget(splitter)
        widget = QWidget()
        widget.setLayout(outer)
        return widget

    def refresh(self) -> None:
        self.refreshing = True
        try:
            current_payment = self.current_payment_id
            current_expense = self.current_expense_id
            self.plans = list_budget_plans()
            self.students = list_students()
            self.buckets = list_fund_buckets()
            self.items = list_budget_items()
            self.transactions = list_transactions()
            active = active_or_latest_plan(self.plans)
            default_plan_id = active.get("plan_id") if active else None
            for combo in [self.payment_plan_combo, self.expense_plan_combo]:
                set_combo_options(
                    combo,
                    self.plans,
                    plan_label,
                    "plan_id",
                    preferred_value=current_combo_value(combo) or default_plan_id,
                )
            self.refresh_approver_combos()
        finally:
            self.refreshing = False
        self.refresh_payment_students()
        self.refresh_expense_buckets()
        if current_payment:
            self.payment_table.select_record_by_key("transaction_id", current_payment)
        if current_expense:
            self.expense_table.select_record_by_key("transaction_id", current_expense)

    def refresh_approver_combos(self) -> None:
        approvers = [
            student
            for student in self.students
            if student.get("can_approve") and student.get("status") == "Active"
        ]
        for combo in [self.payment_approver, self.expense_approver]:
            set_combo_options(combo, approvers, student_label, "student_id", include_blank=True, blank_label="None")

    def student_name(self, student_id: str | None) -> str:
        if not student_id:
            return ""
        student = map_by(self.students, "student_id").get(student_id)
        return student_label(student) if student else student_id

    def item_name(self, item_id: int | None) -> str:
        item = map_by(self.items, "budget_item_id").get(item_id)
        return item.get("item_name") if item else ""

    def bucket_name_for_item(self, item_id: int | None) -> str:
        item = map_by(self.items, "budget_item_id").get(item_id)
        if not item:
            return ""
        bucket = map_by(self.buckets, "bucket_id").get(item.get("bucket_id"))
        return bucket.get("bucket_name") if bucket else ""

    def line_summary(self, transaction: dict) -> str:
        line_items = transaction.get("line_items") or []
        if not line_items:
            return ""
        if len(line_items) == 1:
            item = line_items[0]
            return f"{item.get('item_name')} x{item.get('quantity')}"
        return f"{len(line_items)} line items"

    def plan_students(self, plan_id: int | None) -> list[dict]:
        plan = map_by(self.plans, "plan_id").get(plan_id)
        ids = set(plan.get("student_ids") or []) if plan else set()
        return [student for student in self.students if student.get("student_id") in ids]

    def refresh_payment_students(self, *_args) -> None:
        if self.refreshing:
            return
        plan_id = current_combo_value(self.payment_plan_combo)
        students = self.plan_students(plan_id)
        set_combo_options(
            self.payment_student_combo,
            students,
            student_label,
            "student_id",
            include_blank=not bool(students),
            blank_label="No students in selected plan",
        )
        rows = [
            tx
            for tx in self.transactions
            if tx.get("transaction_type") == "PAYMENT" and tx.get("plan_id") == plan_id
        ]
        self.payment_table.set_rows(rows)
        self.default_payment_amount()

    def default_payment_amount(self, *_args) -> None:
        if self.current_payment_id:
            return
        plan = map_by(self.plans, "plan_id").get(current_combo_value(self.payment_plan_combo))
        if plan:
            self.payment_amount.setValue(float(plan.get("semestral_fee_amount") or 0.01))

    def new_payment(self) -> None:
        self.current_payment_id = None
        self.payment_date.setText(now_text())
        set_combo_value(self.payment_approval, "Pending")
        set_combo_value(self.payment_status, "Active")
        set_combo_value(self.payment_approver, None)
        self.payment_receipt.clear()
        self.payment_notes.clear()
        self.default_payment_amount()

    def load_selected_payment(self) -> None:
        record = self.payment_table.selected_record()
        if not record:
            return
        self.current_payment_id = record.get("transaction_id")
        set_combo_value(self.payment_plan_combo, record.get("plan_id"))
        self.refresh_payment_students()
        set_combo_value(self.payment_student_combo, record.get("student_id"))
        self.payment_amount.setValue(float(record.get("amount") or 0.01))
        self.payment_date.setText(str(record.get("transaction_date") or "")[:16])
        set_combo_value(self.payment_approval, record.get("approval_status") or "Pending")
        set_combo_value(self.payment_approver, record.get("approver_id"))
        set_combo_value(self.payment_status, record.get("transaction_status") or "Active")
        self.payment_receipt.setText(record.get("receipt_path") or "")
        self.payment_notes.setPlainText(record.get("notes") or "")

    def payment_payload(self) -> dict:
        return {
            "transaction_type": "PAYMENT",
            "plan_id": current_combo_value(self.payment_plan_combo),
            "student_id": current_combo_value(self.payment_student_combo),
            "amount": self.payment_amount.value(),
            "transaction_date": input_text(self.payment_date),
            "approval_status": current_combo_value(self.payment_approval),
            "approver_id": current_combo_value(self.payment_approver),
            "transaction_status": current_combo_value(self.payment_status),
            "receipt_path": optional_text(self.payment_receipt),
            "notes": optional_text(self.payment_notes),
        }

    def save_payment(self) -> None:
        try:
            if self.current_payment_id:
                result = update_transaction(self.current_payment_id, self.payment_payload())
                if not result:
                    raise ValueError("Selected payment no longer exists")
            else:
                result = create_transaction(self.payment_payload())
            self.current_payment_id = result["transaction_id"]
            self.main.refresh_all()
            self.tabs.setCurrentIndex(0)
            self.payment_table.select_record_by_key("transaction_id", self.current_payment_id)
            self.show_info("Payment saved.")
        except Exception as error:
            self.show_error(error)

    def delete_payment(self) -> None:
        if not self.current_payment_id:
            self.show_error("Select a payment first.")
            return
        if not self.confirm(f"Delete payment #{self.current_payment_id}?"):
            return
        try:
            delete_transaction(self.current_payment_id)
            self.current_payment_id = None
            self.main.refresh_all()
        except Exception as error:
            self.show_error(error)

    def refresh_expense_buckets(self, *_args) -> None:
        if self.refreshing:
            return
        plan_id = current_combo_value(self.expense_plan_combo)
        buckets = [bucket for bucket in self.buckets if bucket.get("plan_id") == plan_id]
        set_combo_options(self.expense_bucket_combo, buckets, bucket_label, "bucket_id")
        rows = [
            tx
            for tx in self.transactions
            if tx.get("transaction_type") == "EXPENSE" and tx.get("plan_id") == plan_id
        ]
        self.expense_table.set_rows(rows)
        self.refresh_expense_items()

    def refresh_expense_items(self, *_args) -> None:
        if self.refreshing:
            return
        bucket_id = current_combo_value(self.expense_bucket_combo)
        items = [item for item in self.items if item.get("bucket_id") == bucket_id]
        set_combo_options(self.expense_item_combo, items, item_label, "budget_item_id")
        self.update_line_totals()

    def new_expense(self) -> None:
        self.current_expense_id = None
        self.expense_line_items = []
        self.editing_line_index = None
        self.line_table.set_rows([])
        self.expense_date.setText(now_text())
        set_combo_value(self.expense_approval, "Pending")
        set_combo_value(self.expense_approver, None)
        set_combo_value(self.expense_status, "Active")
        self.expense_receipt.clear()
        self.expense_notes.clear()
        self.clear_total_override()
        self.capture_inventory.setChecked(False)
        self.update_line_totals()

    def load_selected_expense(self) -> None:
        record = self.expense_table.selected_record()
        if not record:
            return
        self.current_expense_id = record.get("transaction_id")
        set_combo_value(self.expense_plan_combo, record.get("plan_id"))
        self.refresh_expense_buckets()
        item = map_by(self.items, "budget_item_id").get(record.get("budget_item_id"))
        if item:
            set_combo_value(self.expense_bucket_combo, item.get("bucket_id"))
            self.refresh_expense_items()
        set_combo_value(self.expense_item_combo, record.get("budget_item_id"))
        self.expense_line_items = [dict(item) for item in (record.get("line_items") or [])]
        self.editing_line_index = None
        self.line_table.set_rows(self.expense_line_items)
        self.expense_date.setText(str(record.get("transaction_date") or "")[:16])
        set_combo_value(self.expense_approval, record.get("approval_status") or "Pending")
        set_combo_value(self.expense_approver, record.get("approver_id"))
        set_combo_value(self.expense_status, record.get("transaction_status") or "Active")
        self.expense_receipt.setText(record.get("receipt_path") or "")
        self.expense_notes.setPlainText(record.get("notes") or "")
        has_override = abs(float(record.get("amount_delta") or 0)) > 0.009
        self.override_enabled = has_override
        self.override_amount_value = float(record.get("amount") or 0) if has_override else None
        self.override_reason_value = record.get("amount_override_reason") if has_override else None
        self.capture_inventory.setChecked(False)
        self.update_line_totals()

    def selected_line_index(self) -> int | None:
        record = self.line_table.selected_record()
        if not record:
            return None
        selected_row = self.line_table.currentRow()
        visible_record = (
            self.line_table.visible_rows[selected_row]
            if 0 <= selected_row < len(self.line_table.visible_rows)
            else record
        )
        for index, item in enumerate(self.expense_line_items):
            if item is visible_record:
                return index
        for index, item in enumerate(self.expense_line_items):
            if item == record:
                return index
        return None

    def add_line_item(self) -> None:
        dialog = LineItemDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.expense_line_items.append(dialog.payload())
        self.line_table.set_rows(self.expense_line_items)
        self.update_line_totals()

    def edit_line_item(self) -> None:
        index = self.selected_line_index()
        if index is None:
            self.show_error("Select a line item first.")
            return
        existing = self.expense_line_items[index]
        dialog = LineItemDialog(self, existing)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        updated = dialog.payload()
        if existing.get("line_item_id"):
            updated["line_item_id"] = existing["line_item_id"]
        self.expense_line_items[index] = updated
        self.line_table.set_rows(self.expense_line_items)
        self.line_table.selectRow(index)
        self.update_line_totals()

    def save_line_item(self) -> None:
        self.add_line_item()

    def load_selected_line_item(self) -> None:
        record = self.line_table.selected_record()
        if not record:
            return
        self.purchase_item_name.setText(record.get("item_name") or "")
        self.purchase_qty.setValue(int(record.get("quantity") or 1))
        self.purchase_unit_cost.setValue(float(record.get("unit_cost") or 0.0))

    def remove_line_item(self) -> None:
        index = self.selected_line_index()
        if index is None:
            self.show_error("Select a line item first.")
            return
        self.expense_line_items.pop(index)
        self.editing_line_index = None
        self.line_table.set_rows(self.expense_line_items)
        self.update_line_totals()

    def expense_line_total(self) -> float:
        return sum(
            float(item.get("quantity") or 0) * float(item.get("unit_cost") or 0)
            for item in self.expense_line_items
        )

    def selected_expense_item(self) -> dict | None:
        return map_by(self.items, "budget_item_id").get(current_combo_value(self.expense_item_combo))

    def selected_item_reserved_total(self) -> float:
        item_id = current_combo_value(self.expense_item_combo)
        if not item_id:
            return 0.0
        total = 0.0
        for transaction in self.transactions:
            if transaction.get("transaction_id") == self.current_expense_id:
                continue
            if transaction.get("transaction_type") != "EXPENSE":
                continue
            if transaction.get("budget_item_id") != item_id:
                continue
            if transaction.get("transaction_status") != "Active":
                continue
            if transaction.get("approval_status") not in ("Pending", "Approved"):
                continue
            total += float(transaction.get("amount") or 0)
        return total

    def expense_reserves_budget(self) -> bool:
        return (
            current_combo_value(self.expense_status) == "Active"
            and current_combo_value(self.expense_approval) in ("Pending", "Approved")
        )

    def expense_ledger_amount(self) -> float:
        if self.override_enabled and self.override_amount_value is not None:
            return float(self.override_amount_value)
        return self.expense_line_total()

    def update_line_totals(self, *_args) -> None:
        total = self.expense_line_total()
        for item in self.expense_line_items:
            item["line_total"] = float(item.get("quantity") or 0) * float(item.get("unit_cost") or 0)
        self.computed_total.setText(money(total))
        ledger_amount = self.expense_ledger_amount()
        self.ledger_total.setText(money(ledger_amount))
        if self.override_enabled:
            self.override_summary.setText(self.override_reason_value or "Override set")
        else:
            self.override_summary.setText("No override")

        item = self.selected_expense_item()
        cap = float(item.get("planned_amount") or 0) if item else 0.0
        reserved = self.selected_item_reserved_total()
        remaining = cap - reserved
        after_this = remaining - ledger_amount if self.expense_reserves_budget() else remaining
        self.budget_cap_label.setText(money(cap))
        self.budget_reserved_label.setText(money(reserved))
        self.budget_remaining_label.setText(
            f"{money(remaining)} ({money(after_this)} after this expense)"
            if item
            else "Select a budget item"
        )

    def clear_total_override(self) -> None:
        self.override_enabled = False
        self.override_amount_value = None
        self.override_reason_value = None
        self.update_line_totals()

    def open_override_dialog(self) -> None:
        computed = self.expense_line_total()
        item = self.selected_expense_item()
        remaining = None
        if item and self.expense_reserves_budget():
            remaining = float(item.get("planned_amount") or 0) - self.selected_item_reserved_total()
        dialog = OverrideTotalDialog(
            self,
            computed_total=computed,
            remaining_budget=remaining,
            current_amount=self.expense_ledger_amount() or computed,
            reason=self.override_reason_value,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.override_enabled, self.override_amount_value, self.override_reason_value = dialog.payload()
        self.update_line_totals()

    def sync_inventory_capture(self, *_args) -> None:
        self.purchase_inventory_box.setVisible(self.capture_inventory.isChecked())

    def precheck_expense_cap(self) -> None:
        if not self.expense_reserves_budget():
            return
        item = self.selected_expense_item()
        if not item:
            return
        remaining = float(item.get("planned_amount") or 0) - self.selected_item_reserved_total()
        amount = self.expense_ledger_amount()
        if amount > remaining + 0.009:
            raise ValueError(
                "Expense exceeds the selected budget item cap. "
                f"Remaining: {money(remaining)}. Expense amount: {money(amount)}."
            )

    def expense_payload(self) -> dict:
        if not self.expense_line_items:
            raise ValueError("Add at least one expense line item.")
        self.precheck_expense_cap()
        payload = {
            "transaction_type": "EXPENSE",
            "plan_id": current_combo_value(self.expense_plan_combo),
            "budget_item_id": current_combo_value(self.expense_item_combo),
            "transaction_date": input_text(self.expense_date),
            "approval_status": current_combo_value(self.expense_approval),
            "approver_id": current_combo_value(self.expense_approver),
            "transaction_status": current_combo_value(self.expense_status),
            "receipt_path": optional_text(self.expense_receipt),
            "notes": optional_text(self.expense_notes),
            "line_items": [
                {
                    key: item[key]
                    for key in ["line_item_id", "item_name", "quantity", "unit_cost"]
                    if key in item
                }
                for item in self.expense_line_items
            ],
        }
        if self.override_enabled and self.override_amount_value is not None:
            payload["amount"] = self.override_amount_value
            payload["amount_override_reason"] = self.override_reason_value
        return payload

    def save_expense(self) -> None:
        try:
            if self.current_expense_id:
                result = update_transaction(self.current_expense_id, self.expense_payload())
                if not result:
                    raise ValueError("Selected expense no longer exists")
            else:
                result = create_transaction(self.expense_payload())
            self.current_expense_id = result["transaction_id"]
            if self.capture_inventory.isChecked():
                self.create_purchased_inventory_from_expense(result)
            self.main.refresh_all()
            self.tabs.setCurrentIndex(1)
            self.expense_table.select_record_by_key("transaction_id", self.current_expense_id)
            self.show_info("Expense saved.")
        except Exception as error:
            self.show_error(error)

    def create_purchased_inventory_from_expense(self, transaction: dict) -> None:
        item_name = input_text(self.purchase_item_name)
        if not item_name:
            raise ValueError("Inventory item name is required when inventory capture is enabled.")
        create_inventory_item(
            {
                "source_type": "Purchase",
                "transaction_id": transaction["transaction_id"],
                "item_name": item_name,
                "quantity": self.purchase_qty.value(),
                "unit_cost": optional_money(self.purchase_unit_cost),
                "item_condition": current_combo_value(self.purchase_condition) or None,
                "status": current_combo_value(self.purchase_status),
                "date_recorded": today_text(),
            }
        )

    def delete_expense(self) -> None:
        if not self.current_expense_id:
            self.show_error("Select an expense first.")
            return
        if not self.confirm(f"Delete expense #{self.current_expense_id}?"):
            return
        try:
            delete_transaction(self.current_expense_id)
            self.current_expense_id = None
            self.main.refresh_all()
        except Exception as error:
            self.show_error(error)

    def choose_receipt(self, target: QLineEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select receipt")
        if path:
            target.setText(path)

    def open_payment_workflow(self) -> None:
        self.tabs.setCurrentIndex(0)
        self.new_payment()

    def open_expense_workflow(self) -> None:
        self.tabs.setCurrentIndex(1)
        self.new_expense()


class InventoryTab(AppTab):
    def __init__(self, main: "MainWindow") -> None:
        super().__init__(main)
        self.transactions: list[dict] = []
        self.inventory: list[dict] = []
        self.current_purchase_id: int | None = None
        self.current_legacy_id: int | None = None

        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_purchase_tab(), "Purchased Inventory")
        self.tabs.addTab(self.build_legacy_tab(), "Legacy Inventory")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

    def build_purchase_tab(self) -> QWidget:
        self.purchase_table = DataTable(
            [
                ("ID", lambda row: row.get("inventory_item_id")),
                ("Item", lambda row: row.get("item_name")),
                ("Qty", lambda row: row.get("quantity")),
                ("Unit Cost", lambda row: money(row.get("unit_cost"))),
                ("Condition", lambda row: row.get("item_condition")),
                ("Transaction", lambda row: row.get("transaction_id")),
                ("Status", lambda row: row.get("status")),
            ]
        )
        self.purchase_table.itemSelectionChanged.connect(self.load_selected_purchase)

        left = QVBoxLayout()
        left.addWidget(table_search(self.purchase_table, "Search purchased inventory"))
        left.addWidget(self.purchase_table)

        self.purchase_tx_combo = QComboBox()
        self.purchase_tx_combo.currentIndexChanged.connect(self.refresh_purchase_line_items)
        self.purchase_line_combo = QComboBox()
        self.purchase_line_combo.currentIndexChanged.connect(self.default_purchase_from_line)
        self.purchase_item = QLineEdit()
        self.purchase_qty = make_quantity_input()
        self.purchase_cost = make_money_input(required=False)
        self.purchase_condition = make_combo(["", "New", "Good", "Needs Repair", "Retired"])
        self.purchase_status = make_combo(["Active", "Archived"])
        self.purchase_date = QLineEdit(today_text())
        self.purchase_note = QTextEdit()
        self.purchase_note.setMaximumHeight(90)

        form = QFormLayout()
        form.addRow("Expense Transaction", self.purchase_tx_combo)
        form.addRow("Expense Line", self.purchase_line_combo)
        form.addRow("Item Name", self.purchase_item)
        form.addRow("Quantity", self.purchase_qty)
        form.addRow("Unit Cost", self.purchase_cost)
        form.addRow("Condition", self.purchase_condition)
        form.addRow("Status", self.purchase_status)
        form.addRow("Date Recorded", self.purchase_date)
        form.addRow("Note", self.purchase_note)

        new_button = QPushButton("New Purchased Item")
        new_button.clicked.connect(self.new_purchase)
        save_button = QPushButton("Save Purchased Item")
        save_button.clicked.connect(self.save_purchase)
        delete_button = QPushButton("Delete Purchased Item")
        delete_button.clicked.connect(self.delete_purchase)
        buttons = QHBoxLayout()
        buttons.addWidget(new_button)
        buttons.addWidget(save_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        right = QVBoxLayout()
        right.addWidget(group_box("Purchased Item Details", form))
        right.addLayout(buttons)
        right.addStretch()
        return self.two_pane(left, right)

    def build_legacy_tab(self) -> QWidget:
        self.legacy_table = DataTable(
            [
                ("ID", lambda row: row.get("inventory_item_id")),
                ("Item", lambda row: row.get("item_name")),
                ("Qty", lambda row: row.get("quantity")),
                ("Unit Cost", lambda row: money(row.get("unit_cost"))),
                ("Condition", lambda row: row.get("item_condition")),
                ("Status", lambda row: row.get("status")),
                ("Date", lambda row: row.get("date_recorded")),
            ]
        )
        self.legacy_table.itemSelectionChanged.connect(self.load_selected_legacy)

        left = QVBoxLayout()
        left.addWidget(table_search(self.legacy_table, "Search legacy inventory"))
        left.addWidget(self.legacy_table)

        self.legacy_item = QLineEdit()
        self.legacy_qty = make_quantity_input()
        self.legacy_cost = make_money_input(required=False)
        self.legacy_condition = make_combo(["", "New", "Good", "Needs Repair", "Retired"])
        self.legacy_status = make_combo(["Active", "Archived"])
        self.legacy_date = QLineEdit(today_text())
        self.legacy_note = QTextEdit()
        self.legacy_note.setMaximumHeight(120)

        form = QFormLayout()
        form.addRow("Item Name", self.legacy_item)
        form.addRow("Quantity", self.legacy_qty)
        form.addRow("Unit Cost", self.legacy_cost)
        form.addRow("Condition", self.legacy_condition)
        form.addRow("Status", self.legacy_status)
        form.addRow("Date Recorded", self.legacy_date)
        form.addRow("Source Note", self.legacy_note)

        new_button = QPushButton("New Legacy Item")
        new_button.clicked.connect(self.new_legacy)
        save_button = QPushButton("Save Legacy Item")
        save_button.clicked.connect(self.save_legacy)
        delete_button = QPushButton("Delete Legacy Item")
        delete_button.clicked.connect(self.delete_legacy)
        buttons = QHBoxLayout()
        buttons.addWidget(new_button)
        buttons.addWidget(save_button)
        buttons.addWidget(delete_button)
        buttons.addStretch()

        right = QVBoxLayout()
        right.addWidget(group_box("Legacy Item Details", form))
        right.addLayout(buttons)
        right.addStretch()
        return self.two_pane(left, right)

    def two_pane(self, left: QVBoxLayout, right: QVBoxLayout) -> QWidget:
        splitter = QSplitter()
        left_widget = QWidget()
        left_widget.setLayout(left)
        right_widget = QWidget()
        right_widget.setLayout(right)
        splitter.addWidget(left_widget)
        splitter.addWidget(make_scrollable(right_widget))
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        outer = QVBoxLayout()
        outer.addWidget(splitter)
        widget = QWidget()
        widget.setLayout(outer)
        return widget

    def refresh(self) -> None:
        self.refreshing = True
        try:
            purchase_id = self.current_purchase_id
            legacy_id = self.current_legacy_id
            self.transactions = [
                tx for tx in list_transactions() if tx.get("transaction_type") == "EXPENSE"
            ]
            self.inventory = list_inventory_items()
            set_combo_options(
                self.purchase_tx_combo,
                self.transactions,
                expense_label,
                "transaction_id",
                include_blank=True,
                blank_label="Select expense",
                preferred_value=current_combo_value(self.purchase_tx_combo),
            )
        finally:
            self.refreshing = False
        self.purchase_table.set_rows(
            [item for item in self.inventory if item.get("source_type") == "Purchase"]
        )
        self.legacy_table.set_rows(
            [item for item in self.inventory if item.get("source_type") == "Legacy"]
        )
        self.refresh_purchase_line_items()
        if purchase_id:
            self.purchase_table.select_record_by_key("inventory_item_id", purchase_id)
        if legacy_id:
            self.legacy_table.select_record_by_key("inventory_item_id", legacy_id)

    def refresh_purchase_line_items(self, *_args) -> None:
        if self.refreshing:
            return
        transaction = map_by(self.transactions, "transaction_id").get(current_combo_value(self.purchase_tx_combo))
        line_items = transaction.get("line_items") if transaction else []
        set_combo_options(
            self.purchase_line_combo,
            line_items or [],
            line_item_label,
            "line_item_id",
            include_blank=True,
            blank_label="No specific line",
            preferred_value=current_combo_value(self.purchase_line_combo),
        )
        self.default_purchase_from_line()

    def default_purchase_from_line(self, *_args) -> None:
        line_id = current_combo_value(self.purchase_line_combo)
        transaction = map_by(self.transactions, "transaction_id").get(current_combo_value(self.purchase_tx_combo))
        if not transaction or not line_id:
            return
        line = map_by(transaction.get("line_items") or [], "line_item_id").get(line_id)
        if not line:
            return
        if not self.current_purchase_id or not input_text(self.purchase_item):
            self.purchase_item.setText(line.get("item_name") or "")
        self.purchase_qty.setValue(int(line.get("quantity") or 1))
        self.purchase_cost.setValue(float(line.get("unit_cost") or 0.0))

    def new_purchase(self) -> None:
        self.current_purchase_id = None
        self.purchase_item.clear()
        self.purchase_qty.setValue(1)
        self.purchase_cost.setValue(0.0)
        set_combo_value(self.purchase_condition, "")
        set_combo_value(self.purchase_status, "Active")
        self.purchase_date.setText(today_text())
        self.purchase_note.clear()

    def load_selected_purchase(self) -> None:
        record = self.purchase_table.selected_record()
        if not record:
            return
        self.current_purchase_id = record.get("inventory_item_id")
        set_combo_value(self.purchase_tx_combo, record.get("transaction_id"))
        self.refresh_purchase_line_items()
        set_combo_value(self.purchase_line_combo, record.get("expense_line_item_id"))
        self.purchase_item.setText(record.get("item_name") or "")
        self.purchase_qty.setValue(int(record.get("quantity") or 1))
        self.purchase_cost.setValue(float(record.get("unit_cost") or 0.0))
        set_combo_value(self.purchase_condition, record.get("item_condition") or "")
        set_combo_value(self.purchase_status, record.get("status") or "Active")
        self.purchase_date.setText(record.get("date_recorded") or today_text())
        self.purchase_note.setPlainText(record.get("source_note") or "")

    def purchase_payload(self) -> dict:
        return {
            "source_type": "Purchase",
            "transaction_id": current_combo_value(self.purchase_tx_combo),
            "expense_line_item_id": current_combo_value(self.purchase_line_combo),
            "item_name": input_text(self.purchase_item),
            "quantity": self.purchase_qty.value(),
            "unit_cost": optional_money(self.purchase_cost),
            "item_condition": current_combo_value(self.purchase_condition) or None,
            "status": current_combo_value(self.purchase_status),
            "date_recorded": input_text(self.purchase_date),
            "source_note": optional_text(self.purchase_note),
        }

    def save_purchase(self) -> None:
        try:
            if self.current_purchase_id:
                result = update_inventory_item(self.current_purchase_id, self.purchase_payload())
                if not result:
                    raise ValueError("Selected inventory item no longer exists")
            else:
                result = create_inventory_item(self.purchase_payload())
            self.current_purchase_id = result["inventory_item_id"]
            self.main.refresh_all()
            self.tabs.setCurrentIndex(0)
            self.purchase_table.select_record_by_key("inventory_item_id", self.current_purchase_id)
            self.show_info("Purchased inventory saved.")
        except Exception as error:
            self.show_error(error)

    def delete_purchase(self) -> None:
        if not self.current_purchase_id:
            self.show_error("Select a purchased inventory item first.")
            return
        if not self.confirm(f"Delete inventory item #{self.current_purchase_id}?"):
            return
        try:
            delete_inventory_item(self.current_purchase_id)
            self.current_purchase_id = None
            self.main.refresh_all()
        except Exception as error:
            self.show_error(error)

    def new_legacy(self) -> None:
        self.current_legacy_id = None
        self.legacy_item.clear()
        self.legacy_qty.setValue(1)
        self.legacy_cost.setValue(0.0)
        set_combo_value(self.legacy_condition, "")
        set_combo_value(self.legacy_status, "Active")
        self.legacy_date.setText(today_text())
        self.legacy_note.clear()

    def load_selected_legacy(self) -> None:
        record = self.legacy_table.selected_record()
        if not record:
            return
        self.current_legacy_id = record.get("inventory_item_id")
        self.legacy_item.setText(record.get("item_name") or "")
        self.legacy_qty.setValue(int(record.get("quantity") or 1))
        self.legacy_cost.setValue(float(record.get("unit_cost") or 0.0))
        set_combo_value(self.legacy_condition, record.get("item_condition") or "")
        set_combo_value(self.legacy_status, record.get("status") or "Active")
        self.legacy_date.setText(record.get("date_recorded") or today_text())
        self.legacy_note.setPlainText(record.get("source_note") or "")

    def legacy_payload(self) -> dict:
        return {
            "source_type": "Legacy",
            "item_name": input_text(self.legacy_item),
            "quantity": self.legacy_qty.value(),
            "unit_cost": optional_money(self.legacy_cost),
            "item_condition": current_combo_value(self.legacy_condition) or None,
            "status": current_combo_value(self.legacy_status),
            "date_recorded": input_text(self.legacy_date),
            "source_note": optional_text(self.legacy_note),
        }

    def save_legacy(self) -> None:
        try:
            if self.current_legacy_id:
                result = update_inventory_item(self.current_legacy_id, self.legacy_payload())
                if not result:
                    raise ValueError("Selected legacy inventory item no longer exists")
            else:
                result = create_inventory_item(self.legacy_payload())
            self.current_legacy_id = result["inventory_item_id"]
            self.main.refresh_all()
            self.tabs.setCurrentIndex(1)
            self.legacy_table.select_record_by_key("inventory_item_id", self.current_legacy_id)
            self.show_info("Legacy inventory saved.")
        except Exception as error:
            self.show_error(error)

    def delete_legacy(self) -> None:
        if not self.current_legacy_id:
            self.show_error("Select a legacy inventory item first.")
            return
        if not self.confirm(f"Delete inventory item #{self.current_legacy_id}?"):
            return
        try:
            delete_inventory_item(self.current_legacy_id)
            self.current_legacy_id = None
            self.main.refresh_all()
        except Exception as error:
            self.show_error(error)

    def open_legacy_workflow(self) -> None:
        self.tabs.setCurrentIndex(1)
        self.new_legacy()


class ReportsTab(AppTab):
    def __init__(self, main: "MainWindow") -> None:
        super().__init__(main)
        self.plans: list[dict] = []
        self.plan_combo = QComboBox()
        self.report_combo = QComboBox()
        for report_type in REPORT_TYPES:
            self.report_combo.addItem(report_type.replace("-", " ").title(), report_type)
        self.plan_combo.currentIndexChanged.connect(self.load_preview)
        self.report_combo.currentIndexChanged.connect(self.load_preview)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh)
        export_button = QPushButton("Export PDF")
        export_button.clicked.connect(self.export_pdf)

        top = QHBoxLayout()
        top.addWidget(QLabel("Plan"))
        top.addWidget(self.plan_combo, 1)
        top.addWidget(QLabel("Report"))
        top.addWidget(self.report_combo)
        top.addWidget(refresh_button)
        top.addWidget(export_button)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.preview, 1)

    def refresh(self) -> None:
        self.refreshing = True
        try:
            self.plans = list_budget_plans()
            active = active_or_latest_plan(self.plans)
            set_combo_options(
                self.plan_combo,
                self.plans,
                plan_label,
                "plan_id",
                preferred_value=active.get("plan_id") if active else None,
            )
        finally:
            self.refreshing = False
        self.load_preview()

    def load_preview(self, *_args) -> None:
        if self.refreshing:
            return
        try:
            report_type = current_combo_value(self.report_combo)
            plan_id = current_combo_value(self.plan_combo)
            if not report_type or not plan_id:
                self.preview.setPlainText("Create or select a budget plan to preview reports.")
                return
            data = get_report_data(report_type, plan_id)
            self.preview.setPlainText(self.format_report(data))
        except Exception as error:
            self.preview.setPlainText(str(error))

    def format_report(self, data: dict) -> str:
        report_type = data.get("report_type")
        lines = [f"{report_type.replace('-', ' ').title()} Report", ""]
        plan = data.get("plan") or data.get("budget_plan", {}).get("plan") or {}
        if plan:
            lines.extend(
                [
                    f"Plan: {plan.get('academic_year')} {plan.get('semester')}",
                    f"Total Planned Budget: {money(plan.get('total_planned_budget'))}",
                    f"Semestral Fee: {money(plan.get('semestral_fee_amount'))}",
                    f"Members: {plan.get('member_count')}",
                    "",
                ]
            )

        if report_type == "budget-plan":
            lines.append("Fund Buckets")
            for bucket in data.get("fund_buckets", []):
                lines.append(f"- {bucket.get('bucket_name')}: {money(bucket.get('planned_amount'))}")
            lines.append("")
            lines.append("Budget Items")
            for item in data.get("budget_items", []):
                lines.append(f"- {item.get('item_name')}: {money(item.get('planned_amount'))}")
        elif report_type == "collection":
            lines.append("Paid Students")
            for student in data.get("paid_students", []):
                lines.append(f"- {student.get('student_id')} {student.get('name')}")
            lines.append("")
            lines.append("Pending Students")
            for student in data.get("pending_students", []):
                lines.append(f"- {student.get('student_id')} {student.get('name')}")
        elif report_type == "expense":
            lines.append("Expenses")
            for expense in data.get("expenses", []):
                lines.append(
                    f"- #{expense.get('transaction_id')} {expense.get('bucket_name')} > "
                    f"{expense.get('budget_item_name')}: {money(expense.get('amount'))} "
                    f"({expense.get('approval_status')}/{expense.get('transaction_status')})"
                )
                if expense.get("line_item_summary"):
                    lines.append(f"  {expense.get('line_item_summary')}")
        elif report_type == "inventory":
            lines.append("Inventory")
            for item in data.get("inventory_items", []):
                lines.append(
                    f"- #{item.get('inventory_item_id')} {item.get('item_name')} "
                    f"x{item.get('quantity')} ({item.get('source_type')})"
                )
        else:
            summary = data.get("dashboard_summary", {})
            totals = summary.get("totals", {})
            collection = summary.get("collection_progress", {})
            inventory = summary.get("inventory_summary", {})
            lines.extend(
                [
                    "Transparency Summary",
                    f"Payments: {money(totals.get('payments'))}",
                    f"Expenses: {money(totals.get('expenses'))}",
                    f"Available Funds: {money(totals.get('available_funds'))}",
                    f"Paid Students: {collection.get('paid_count', 0)}",
                    f"Pending Students: {collection.get('pending_count', 0)}",
                    f"Inventory Records: {inventory.get('total_items', 0)}",
                ]
            )
        return "\n".join(lines)

    def export_pdf(self) -> None:
        try:
            report_type = current_combo_value(self.report_combo)
            plan_id = current_combo_value(self.plan_combo)
            if not report_type or not plan_id:
                raise ValueError("Select a plan and report type first.")
            default_name = f"glass-{report_type}-report.pdf"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Export PDF",
                default_name,
                "PDF Files (*.pdf)",
            )
            if not path:
                return
            pdf = generate_report_pdf(report_type, plan_id)
            Path(path).write_bytes(pdf)
            self.show_info(f"Report exported to {path}")
        except Exception as error:
            self.show_error(error)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GLASS Budget Liquidation")
        self.resize(1280, 820)

        self.tabs = QTabWidget()
        self.dashboard_tab = DashboardTab(self)
        self.budget_tab = BudgetTab(self)
        self.members_tab = MembersTab(self)
        self.transactions_tab = TransactionsTab(self)
        self.inventory_tab = InventoryTab(self)
        self.reports_tab = ReportsTab(self)

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.budget_tab, "Budget")
        self.tabs.addTab(self.members_tab, "Members")
        self.tabs.addTab(self.transactions_tab, "Transactions")
        self.tabs.addTab(self.inventory_tab, "Inventory")
        self.tabs.addTab(self.reports_tab, "Reports")
        self.tabs.currentChanged.connect(self.refresh_current_tab)
        self.setCentralWidget(self.tabs)
        self.refresh_all()

    def refresh_current_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        refresh = getattr(widget, "refresh", None)
        if callable(refresh):
            refresh()

    def refresh_all(self) -> None:
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            refresh = getattr(widget, "refresh", None)
            if callable(refresh):
                refresh()

    def open_payment_workflow(self) -> None:
        self.tabs.setCurrentWidget(self.transactions_tab)
        self.transactions_tab.open_payment_workflow()

    def open_expense_workflow(self) -> None:
        self.tabs.setCurrentWidget(self.transactions_tab)
        self.transactions_tab.open_expense_workflow()

    def open_legacy_inventory_workflow(self) -> None:
        self.tabs.setCurrentWidget(self.inventory_tab)
        self.inventory_tab.open_legacy_workflow()

    def open_reports_workflow(self) -> None:
        self.tabs.setCurrentWidget(self.reports_tab)
        self.reports_tab.load_preview()


def _apply_stylesheet(app: QApplication) -> None:
    style_path = Path(__file__).resolve().parent / "desktop" / "style.qss"
    if style_path.exists():
        app.setStyleSheet(style_path.read_text(encoding="utf-8"))


def main() -> None:
    init_db()
    app = QApplication(sys.argv)
    _apply_stylesheet(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
