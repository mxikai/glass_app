from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QCheckBox,
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


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    field_type: str = "text"  # text, int, float, bool, list, enum, date, datetime
    placeholder: str = ""
    options: tuple[str, ...] | None = None
    multiline: bool = False


@dataclass(frozen=True)
class ResourceConfig:
    title: str
    list_fn: Callable[[], list[dict]]
    create_fn: Callable[[dict], dict]
    update_fn: Callable[[Any, dict], dict | None]
    delete_fn: Callable[[Any], bool]
    id_field: FieldSpec
    fields: tuple[FieldSpec, ...]
    id_in_create: bool = False


class FormPanel(QGroupBox):
    def __init__(
        self,
        title: str,
        fields: tuple[FieldSpec, ...],
        include_id: bool,
        id_field: FieldSpec | None,
        bool_mode: str,
    ) -> None:
        super().__init__(title)
        self._fields = fields
        self._include_id = include_id
        self._id_field = id_field
        self._bool_mode = bool_mode
        self._widgets: dict[str, QWidget] = {}

        layout = QFormLayout()
        layout.setLabelAlignment(Qt.AlignLeft)
        layout.setFormAlignment(Qt.AlignTop)

        if include_id and id_field:
            layout.addRow(self._create_label(id_field.label), self._create_widget(id_field))

        for field in fields:
            layout.addRow(self._create_label(field.label), self._create_widget(field))

        self.setLayout(layout)

    def _create_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        return label

    def _create_widget(self, field: FieldSpec) -> QWidget:
        if field.field_type == "bool" and self._bool_mode == "tri":
            widget = QComboBox()
            widget.addItem("")
            widget.addItems(["true", "false"])
        elif field.field_type == "bool":
            widget = QCheckBox()
        elif field.field_type == "enum":
            widget = QComboBox()
            widget.addItem("")
            if field.options:
                widget.addItems(list(field.options))
        elif field.multiline:
            widget = QTextEdit()
            widget.setFixedHeight(70)
        else:
            widget = QLineEdit()
            if field.placeholder:
                widget.setPlaceholderText(field.placeholder)

        self._widgets[field.key] = widget
        return widget

    def get_payload(self, include_empty_lists: bool, include_unchecked: bool) -> dict:
        payload: dict[str, Any] = {}

        for field, widget in self._widgets.items():
            value, has_value = self._extract_value(field, widget, include_empty_lists, include_unchecked)
            if not has_value:
                continue
            payload[field] = value

        return payload

    def _extract_value(
        self,
        field_key: str,
        widget: QWidget,
        include_empty_lists: bool,
        include_unchecked: bool,
    ) -> tuple[Any, bool]:
        spec = self._find_spec(field_key)
        if spec is None:
            return None, False

        if isinstance(widget, QCheckBox):
            if include_unchecked:
                return widget.isChecked(), True
            if widget.isChecked():
                return True, True
            return None, False

        if isinstance(widget, QComboBox):
            text = widget.currentText().strip()
            if spec.field_type == "bool":
                if not text:
                    return None, False
                return text == "true", True
            if not text:
                return None, False
            return text, True

        if isinstance(widget, QTextEdit):
            text = widget.toPlainText().strip()
        else:
            text = widget.text().strip()

        if spec.field_type == "list":
            if not text:
                if include_empty_lists:
                    return [], True
                return None, False
            if text == "[]":
                return [], True
            return [item.strip() for item in text.split(",") if item.strip()], True

        if not text:
            return None, False

        if spec.field_type == "int":
            try:
                return int(text), True
            except ValueError as exc:
                raise ValueError(f"Invalid integer for {spec.label}.") from exc

        if spec.field_type == "float":
            try:
                return float(text), True
            except ValueError as exc:
                raise ValueError(f"Invalid number for {spec.label}.") from exc

        if spec.field_type == "enum":
            return text, True

        return text, True

    def _find_spec(self, field_key: str) -> FieldSpec | None:
        if self._id_field and self._id_field.key == field_key:
            return self._id_field
        for field in self._fields:
            if field.key == field_key:
                return field
        return None

    def clear(self) -> None:
        for widget in self._widgets.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QComboBox):
                widget.setCurrentIndex(0)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)


class ResourceTab(QWidget):
    def __init__(self, config: ResourceConfig) -> None:
        super().__init__()
        self._config = config

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(16)

        header = QHBoxLayout()
        header_label = QLabel(f"{config.title} Records")
        header_label.setStyleSheet("font-weight: 600;")
        header.addWidget(header_label)
        header.addStretch()

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_list)
        header.addWidget(refresh_button)
        content_layout.addLayout(header)

        self._table = QTableWidget()
        self._table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._table.setMinimumHeight(220)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        content_layout.addWidget(self._table)

        forms_layout = QHBoxLayout()
        forms_layout.setSpacing(16)

        create_fields = config.fields
        if not config.id_in_create:
            create_fields = tuple(field for field in config.fields if field.key != config.id_field.key)

        self._create_form = FormPanel(
            "Create",
            create_fields,
            include_id=False,
            id_field=None,
            bool_mode="checkbox",
        )
        self._create_button = QPushButton(f"Create {config.title}")
        self._create_button.clicked.connect(self.create_record)
        create_container = self._wrap_form(self._create_form, self._create_button)

        self._update_form = FormPanel(
            "Update",
            config.fields,
            include_id=True,
            id_field=config.id_field,
            bool_mode="tri",
        )
        self._update_button = QPushButton(f"Update {config.title}")
        self._update_button.clicked.connect(self.update_record)
        update_container = self._wrap_form(self._update_form, self._update_button)

        self._delete_form = FormPanel(
            "Delete",
            tuple(),
            include_id=True,
            id_field=config.id_field,
            bool_mode="tri",
        )
        self._delete_button = QPushButton(f"Delete {config.title}")
        self._delete_button.clicked.connect(self.delete_record)
        delete_container = self._wrap_form(self._delete_form, self._delete_button)

        forms_layout.addWidget(create_container)
        forms_layout.addWidget(update_container)
        forms_layout.addWidget(delete_container)

        content_layout.addLayout(forms_layout)

        self._status = QLabel("Ready.")
        self._status.setStyleSheet("color: #555;")
        content_layout.addWidget(self._status)

        content.setLayout(content_layout)
        scroll.setWidget(content)

        layout = QVBoxLayout()
        layout.addWidget(scroll)
        self.setLayout(layout)

    def _wrap_form(self, form: FormPanel, button: QPushButton) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(form)
        layout.addWidget(button)
        layout.addStretch()
        container.setLayout(layout)
        return container

    def refresh_list(self) -> None:
        try:
            rows = self._config.list_fn()
        except Exception as exc:
            self._show_error("Load failed", exc)
            return

        self._populate_table(rows)
        self._set_status(f"Loaded {len(rows)} record(s).")

    def create_record(self) -> None:
        try:
            payload = self._create_form.get_payload(
                include_empty_lists=True,
                include_unchecked=True,
            )
            record = self._config.create_fn(payload)
        except Exception as exc:
            self._show_error("Create failed", exc)
            return

        self._create_form.clear()
        self._set_status(f"Created {self._config.title}.")
        self.refresh_list()

    def update_record(self) -> None:
        try:
            payload = self._update_form.get_payload(
                include_empty_lists=False,
                include_unchecked=False,
            )
        except Exception as exc:
            self._show_error("Update failed", exc)
            return

        record_id = payload.pop(self._config.id_field.key, None)
        if record_id is None:
            self._show_error("Update failed", ValueError("Missing ID."))
            return

        if not payload:
            self._show_error("Update failed", ValueError("No fields to update."))
            return

        try:
            record = self._config.update_fn(record_id, payload)
        except Exception as exc:
            self._show_error("Update failed", exc)
            return

        if record is None:
            self._show_error("Update failed", ValueError("Record not found."))
            return

        self._set_status(f"Updated {self._config.title}.")
        self.refresh_list()

    def delete_record(self) -> None:
        try:
            payload = self._delete_form.get_payload(
                include_empty_lists=False,
                include_unchecked=False,
            )
        except Exception as exc:
            self._show_error("Delete failed", exc)
            return

        record_id = payload.get(self._config.id_field.key)
        if record_id is None:
            self._show_error("Delete failed", ValueError("Missing ID."))
            return

        try:
            deleted = self._config.delete_fn(record_id)
        except Exception as exc:
            self._show_error("Delete failed", exc)
            return

        if not deleted:
            self._show_error("Delete failed", ValueError("Record not found."))
            return

        self._set_status(f"Deleted {self._config.title}.")
        self.refresh_list()

    def _populate_table(self, rows: list[dict]) -> None:
        self._table.clear()
        if not rows:
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            return

        headers = list(rows[0].keys())
        self._table.setColumnCount(len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        self._table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for col_index, key in enumerate(headers):
                value = row.get(key)
                if isinstance(value, list):
                    text = ", ".join(str(item) for item in value)
                else:
                    text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self._table.setItem(row_index, col_index, item)

        self._table.resizeColumnsToContents()

    def _set_status(self, message: str) -> None:
        self._status.setText(message)

    def _show_error(self, title: str, exc: Exception) -> None:
        QMessageBox.critical(self, title, str(exc))
        self._set_status(f"{title}: {exc}")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GLASS Desktop Mock UI")
        self.resize(1024, 768)

        tabs = QTabWidget()
        tabs.addTab(ResourceTab(build_student_config()), "Students")
        tabs.addTab(ResourceTab(build_budget_plan_config()), "Budget Plans")
        tabs.addTab(ResourceTab(build_fund_bucket_config()), "Fund Buckets")
        tabs.addTab(ResourceTab(build_budget_item_config()), "Budget Items")
        tabs.addTab(ResourceTab(build_transaction_config()), "Transactions")
        tabs.addTab(ResourceTab(build_inventory_config()), "Inventory")

        self.setCentralWidget(tabs)


def build_student_config() -> ResourceConfig:
    return ResourceConfig(
        title="Student",
        list_fn=list_students,
        create_fn=create_student,
        update_fn=update_student,
        delete_fn=delete_student,
        id_field=FieldSpec("student_id", "Student ID"),
        fields=(
            FieldSpec("student_id", "Student ID"),
            FieldSpec("name", "Name"),
            FieldSpec("program", "Program"),
            FieldSpec("year_level", "Year Level", "int"),
            FieldSpec("role_title", "Role Title"),
            FieldSpec("can_approve", "Can Approve", "bool"),
            FieldSpec("status", "Status", placeholder="Active"),
        ),
        id_in_create=True,
    )


def build_budget_plan_config() -> ResourceConfig:
    return ResourceConfig(
        title="Budget Plan",
        list_fn=list_budget_plans,
        create_fn=create_budget_plan,
        update_fn=update_budget_plan,
        delete_fn=delete_budget_plan,
        id_field=FieldSpec("plan_id", "Plan ID", "int"),
        fields=(
            FieldSpec("academic_year", "Academic Year", placeholder="2025-2026"),
            FieldSpec("semester", "Semester", placeholder="1st"),
            FieldSpec("total_planned_budget", "Total Planned Budget", "float"),
            FieldSpec("member_count", "Member Count", "int"),
            FieldSpec("semestral_fee_amount", "Semestral Fee Amount", "float"),
            FieldSpec("approval_status", "Approval Status", placeholder="Pending"),
            FieldSpec("approved_date", "Approved Date (YYYY-MM-DD)", "date"),
            FieldSpec("status", "Status", placeholder="Active"),
            FieldSpec("student_ids", "Student IDs (comma separated)", "list"),
        ),
    )


def build_fund_bucket_config() -> ResourceConfig:
    return ResourceConfig(
        title="Fund Bucket",
        list_fn=list_fund_buckets,
        create_fn=create_fund_bucket,
        update_fn=update_fund_bucket,
        delete_fn=delete_fund_bucket,
        id_field=FieldSpec("bucket_id", "Bucket ID", "int"),
        fields=(
            FieldSpec("plan_id", "Plan ID", "int"),
            FieldSpec("bucket_name", "Bucket Name"),
            FieldSpec("planned_amount", "Planned Amount", "float"),
            FieldSpec("description", "Description"),
        ),
    )


def build_budget_item_config() -> ResourceConfig:
    return ResourceConfig(
        title="Budget Item",
        list_fn=list_budget_items,
        create_fn=create_budget_item,
        update_fn=update_budget_item,
        delete_fn=delete_budget_item,
        id_field=FieldSpec("budget_item_id", "Budget Item ID", "int"),
        fields=(
            FieldSpec("bucket_id", "Bucket ID", "int"),
            FieldSpec("item_name", "Item Name"),
            FieldSpec("item_type", "Item Type"),
            FieldSpec("planned_amount", "Planned Amount", "float"),
            FieldSpec("description", "Description"),
        ),
    )


def build_transaction_config() -> ResourceConfig:
    return ResourceConfig(
        title="Transaction",
        list_fn=list_transactions,
        create_fn=create_transaction,
        update_fn=update_transaction,
        delete_fn=delete_transaction,
        id_field=FieldSpec("transaction_id", "Transaction ID", "int"),
        fields=(
            FieldSpec("plan_id", "Plan ID", "int"),
            FieldSpec("transaction_type", "Transaction Type", "enum", options=("PAYMENT", "EXPENSE")),
            FieldSpec("amount", "Amount", "float"),
            FieldSpec("student_id", "Student ID"),
            FieldSpec("approver_id", "Approver ID"),
            FieldSpec("budget_item_id", "Budget Item ID", "int"),
            FieldSpec(
                "transaction_status",
                "Transaction Status",
                placeholder="Active",
            ),
            FieldSpec("approval_status", "Approval Status", placeholder="Pending"),
            FieldSpec(
                "transaction_date",
                "Transaction Date (YYYY-MM-DDTHH:MM)",
                "datetime",
            ),
            FieldSpec("notes", "Notes", multiline=True),
            FieldSpec("receipt_path", "Receipt Path"),
            FieldSpec("current_hash", "Current Hash"),
            FieldSpec("previous_hash", "Previous Hash"),
        ),
    )


def build_inventory_config() -> ResourceConfig:
    return ResourceConfig(
        title="Inventory Item",
        list_fn=list_inventory_items,
        create_fn=create_inventory_item,
        update_fn=update_inventory_item,
        delete_fn=delete_inventory_item,
        id_field=FieldSpec("inventory_item_id", "Inventory Item ID", "int"),
        fields=(
            FieldSpec("transaction_id", "Transaction ID", "int"),
            FieldSpec("item_name", "Item Name"),
            FieldSpec("quantity", "Quantity", "int"),
            FieldSpec("item_condition", "Item Condition"),
            FieldSpec("status", "Status", placeholder="Active"),
            FieldSpec("date_recorded", "Date Recorded (YYYY-MM-DD)", "date"),
        ),
    )


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
