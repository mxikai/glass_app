from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint

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

        # --- THE ANIMATED SLIDING PILL ---
        self.indicator = QWidget(self)
        self.indicator.setStyleSheet("""
            background-color: #EEF0F8;
            border-top-left-radius: 20px;
            border-bottom-left-radius: 20px;
        """)
        self.indicator.resize(60, 44) 
        self.indicator.show()

        self.anim = QPropertyAnimation(self.indicator, b"pos")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        # ---------------------------------

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # App logo/icon at top
        logo = QLabel("💎")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 30px; padding: 10px 0 20px 0;")
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

        self._set_active("dashboard", animate=False)

    def resizeEvent(self, event):
        """Ensures the pill snaps to the right spot instantly when the layout calculates."""
        super().resizeEvent(event)
        for pid, btn in self._buttons.items():
            if btn.isChecked():
                self.anim.stop()
                self.indicator.move(12, btn.y() + 4)

    def _on_nav(self, page_id: str):
        self._set_active(page_id, animate=True)
        self.page_changed.emit(page_id)

    def _set_active(self, page_id: str, animate=True):
        for pid, btn in self._buttons.items():
            btn.setChecked(pid == page_id)
            if pid == page_id:
                if animate:
                    self.anim.stop()
                    self.anim.setEndValue(QPoint(12, btn.y() + 4))
                    self.anim.start()
                else:
                    self.indicator.move(12, btn.y() + 4)