from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


NAV_ITEMS = [
    ("🏠", "Dashboard",    "dashboard"),
    ("👥", "Students",     "students"),
    ("📋", "Budget Plans", "budget"),
    ("💳", "Transactions", "transactions"),
    ("📦", "Inventory",    "inventory"),
    ("📊", "Reports",      "reports"),
]


class Sidebar(QWidget):
    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedWidth(70)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # App logo/icon at top
        logo = QLabel("💎")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 26px; padding: 10px 0 20px 0;")
        layout.addWidget(logo)

        self._buttons = {}
        for icon, tooltip, page_id in NAV_ITEMS:
            btn = QPushButton(icon)
            btn.setObjectName("navBtn")
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedHeight(52)
            btn.clicked.connect(lambda checked, pid=page_id: self._on_nav(pid))
            layout.addWidget(btn)
            self._buttons[page_id] = btn

        layout.addStretch()

        # Avatar at bottom
        avatar = QLabel("FA")
        avatar.setObjectName("avatar")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "background-color: rgba(255,255,255,0.25); color: white;"
            "border-radius: 18px; font-size: 11px; font-weight: 700;"
            "font-family: 'Segoe UI';" 
        )
        layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Set dashboard as active on load
        self._set_active("dashboard")

    def _on_nav(self, page_id: str):
        self._set_active(page_id)
        self.page_changed.emit(page_id)

    def _set_active(self, page_id: str):
        for pid, btn in self._buttons.items():
            btn.setChecked(pid == page_id)
