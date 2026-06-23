import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint, QVariantAnimation
from PyQt6.QtGui import QPixmap, QPainter

# --- BUILD THE PATH TO YOUR ASSETS FOLDER ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(CURRENT_DIR, '..', 'assets')

NAV_ITEMS = [
    ("02-home.png",    "home_active.png",    "Dashboard",    "dashboard"),
    ("03-student.png",     "student_active.png",     "Students",     "students"),
    ("04-records.png",       "records_active.png",       "Budget Plans", "budget"),
    ("05-expenses.png", "expenses_active.png", "Transactions", "transactions"),
    ("06-inventory.png",    "inventory_active.png",    "Inventory",    "inventory"),
    ("07-reports-analytics.png",      "reports_active.png",      "Reports",      "reports"),
]

# ==========================================
# CUSTOM ANIMATED FADE BUTTON
# ==========================================
class AnimatedNavButton(QPushButton):
    def __init__(self, default_icon_path, active_icon_path, tooltip, parent=None):
        super().__init__(parent)
        self.setObjectName("navBtn")
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setFixedHeight(52)
        
        self.default_pixmap = QPixmap(default_icon_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.active_pixmap = QPixmap(active_icon_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        self._fade_val = 0.0
        
        self.fade_anim = QVariantAnimation(self)
        self.fade_anim.setDuration(250)
        self.fade_anim.valueChanged.connect(self._update_fade)
        self.toggled.connect(self._on_toggle)

    def _update_fade(self, value):
        self._fade_val = value
        self.update()

    def _on_toggle(self, checked):
        self.fade_anim.stop()
        self.fade_anim.setStartValue(self._fade_val)
        self.fade_anim.setEndValue(1.0 if checked else 0.0)
        self.fade_anim.start()

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        rect = self.rect()
        x = rect.x() + (rect.width() - 24) // 2
        y = rect.y() + (rect.height() - 24) // 2
        
        painter.setOpacity(1.0 - self._fade_val)
        painter.drawPixmap(x, y, self.default_pixmap)
        
        painter.setOpacity(self._fade_val)
        painter.drawPixmap(x, y, self.active_pixmap)
        
        painter.end()


# ==========================================
# SIDEBAR VIEW
# ==========================================
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
        self.indicator.resize(80, 44) 
        self.indicator.show()

        self.anim = QPropertyAnimation(self.indicator, b"pos")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        # ---------------------------------

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- TOP LOGO SETUP ---
        self.logo = QLabel()
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setStyleSheet("padding: 10px 0 20px 0;")
        
        logo_path = os.path.join(ASSETS_DIR, "01-magnifying-glass.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path).scaled(36, 36, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo.setPixmap(pixmap)
        else:
            self.logo.setText("APP") 
            self.logo.setStyleSheet("color: white; font-weight: bold; font-size: 16px; padding: 10px 0 20px 0;")
        
        layout.addWidget(self.logo)

        # --- BUTTON SETUP ---
        self._buttons = {}
        for default_img, active_img, tooltip, page_id in NAV_ITEMS:
            
            default_path = os.path.join(ASSETS_DIR, default_img)
            active_path = os.path.join(ASSETS_DIR, active_img)
            
            btn = AnimatedNavButton(default_path, active_path, tooltip)
            btn.clicked.connect(lambda checked, pid=page_id: self._on_nav(pid))
            
            layout.addWidget(btn)
            self._buttons[page_id] = btn

        layout.addStretch()

        self._set_active("dashboard", animate=False)

    def resizeEvent(self, event):
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