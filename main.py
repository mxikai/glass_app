import sys
import os

# --- THE MASTER BRIDGE ---
project_root = os.path.dirname(os.path.abspath(__file__))

if project_root not in sys.path:
    sys.path.insert(0, project_root)

backend_path = os.path.join(project_root, 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
# -------------------------

from frontend.components.sidebar import Sidebar
from frontend.views.dashboard import DashboardView
from frontend.views.students import StudentsView
from frontend.views.budgets import BudgetPlanView
from frontend.views.transactions import TransactionsView
from frontend.views.inventory import InventoryView
from frontend.views.reports import ReportsView

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QStackedWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GLASS — Student Organization Budget Manager")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 760)

        # Load stylesheet
        theme_path = os.path.join(project_root, "frontend", "styles", "theme.qss")
        if os.path.exists(theme_path):
            with open(theme_path, "r") as f:
                self.setStyleSheet(f.read())

        # Central widget
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(20, 20, 0, 20) 
        root_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._switch_page)
        root_layout.addWidget(self.sidebar)

        # Page stack
        self.stack = QStackedWidget()
        self.stack.setObjectName("contentArea")
        root_layout.addWidget(self.stack)

        # Register pages in the same order as NAV_ITEMS
        self._pages = {
            "dashboard":    DashboardView(),
            "students":     StudentsView(),
            "budget":       BudgetPlanView(),
            "transactions": TransactionsView(),
            "inventory":    InventoryView(),
            "reports":      ReportsView(),
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

        self._switch_page("dashboard")

    def _switch_page(self, page_id: str):
        page = self._pages.get(page_id)
        if page:
            self.stack.setCurrentWidget(page)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # High-DPI support
    try:
        from PyQt6.QtCore import Qt
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    except Exception:
        pass

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
