from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


def _placeholder(title: str, icon: str, color: str = "#6C5CE7"):
    page = QWidget()
    page.setObjectName("contentArea")
    v = QVBoxLayout(page)
    v.setAlignment(Qt.AlignmentFlag.AlignCenter)

    ico = QLabel(icon)
    ico.setStyleSheet(f"font-size: 52px;")
    ico.setAlignment(Qt.AlignmentFlag.AlignCenter)

    lbl = QLabel(title)
    lbl.setStyleSheet(
        f"font-size: 22px; font-weight: 700; color: #1A1A3E;"
        f"font-family: 'Segoe UI';"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

    sub = QLabel("This page is under construction.\nConnect your Python backend to populate data here.")
    sub.setStyleSheet("font-size: 13px; color: #9B9BB0; font-family: 'Segoe UI';")
    sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sub.setWordWrap(True)

    v.addWidget(ico)
    v.addSpacing(12)
    v.addWidget(lbl)
    v.addSpacing(8)
    v.addWidget(sub)

    return page


class BudgetPlanView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_placeholder("Budget Plans", "📋"))


class TransactionsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_placeholder("Transactions", "💳", "#FD79A8"))


class InventoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_placeholder("Inventory", "📦", "#FDCB6E"))


class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_placeholder("Reports", "📊", "#74B9FF"))
