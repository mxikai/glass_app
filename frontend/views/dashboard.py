import sys
import os

# --- THE MASTER BRIDGE ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.dashboard_service import get_dashboard_summary
from backend.services.transaction_service import list_transactions
from backend.services.budget_service import list_budget_plans
# -------------------------

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QProgressBar, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath

# ==========================================
# CUSTOM UI COMPONENTS
# ==========================================
class MiniChart(QWidget):
    """Draws a smooth, curved line chart for the cash flow."""
    def __init__(self, data: list, line_color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self.data = data
        self.line_color = QColor(line_color)
        self.setMinimumHeight(150)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def update_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Grab the running balance amounts from the backend
        values = [float(point.get('amount', 0)) for point in self.data]
        values.insert(0, 0.0)
        
        # If there are no real transactions yet, draw a flat baseline
        if len(values) == 1:
            values.append(0.0)

        width = self.width()
        height = self.height()
        
        max_val = max(values)
        min_val = min(values)
        
        # Add a tiny buffer so the highest point doesn't clip the top of the frame
        val_range = (max_val - min_val) if max_val != min_val else 1.0

        path = QPainterPath()
        step_x = width / (len(values) - 1)

        start_y = height - ((values[0] - min_val) / val_range * (height - 30)) - 15
        path.moveTo(0, start_y)

        for i in range(1, len(values)):
            x1 = (i - 1) * step_x
            y1 = height - ((values[i - 1] - min_val) / val_range * (height - 30)) - 15
            x2 = i * step_x
            y2 = height - ((values[i] - min_val) / val_range * (height - 30)) - 15

            # Cubic bezier curve logic
            ctrl1_x = x1 + (x2 - x1) / 2
            ctrl1_y = y1
            ctrl2_x = x1 + (x2 - x1) / 2
            ctrl2_y = y2

            path.cubicTo(ctrl1_x, ctrl1_y, ctrl2_x, ctrl2_y, x2, y2)

        pen = QPen(self.line_color, 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(path)


# ==========================================
# MAIN DASHBOARD VIEW
# ==========================================
class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        self.setup_ui()
        self.load_plans()
        
        # Auto-Sync
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.refresh_dashboard)
        self.sync_timer.start(3000) 

    def showEvent(self, event):
        super().showEvent(event)
        self.load_plans()

    def _apply_glow(self, widget):
        """Applies a soft, transparent purple glow to simulate 3D glass depth."""
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(40)
        glow.setColor(QColor(108, 92, 231, 35))
        glow.setOffset(0, 8)
        widget.setGraphicsEffect(glow)
    
    def mousePressEvent(self, event):
        """Clears the table highlight AND resets the form when clicking the background."""
        super().mousePressEvent(event)
        
        from PyQt6.QtWidgets import QTableWidget
        for table in self.findChildren(QTableWidget):
            table.clearSelection()
            
        if hasattr(self, 'clear_form'):
            self.clear_form()
        elif hasattr(self, 'clear_current_form'):
            self.clear_current_form()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(24)

        # --- HEADER ---
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        self.lbl_title = QLabel("Dashboard Overview")
        self.lbl_title.setObjectName("pageTitle")
        
        self.lbl_subtitle = QLabel("Select a plan to view analytics")
        self.lbl_subtitle.setStyleSheet("color: #9B9BB0; font-size: 13px;")
        
        title_layout.addWidget(self.lbl_title)
        title_layout.addWidget(self.lbl_subtitle)
        
        # PLAN SELECTOR DROPDOWN
        self.combo_plan = QComboBox()
        self.combo_plan.setObjectName("formInput")
        self.combo_plan.setFixedWidth(250)
        self.combo_plan.currentIndexChanged.connect(self.refresh_dashboard)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("<b>Active Plan:</b> "))
        header_layout.addWidget(self.combo_plan)
        main_layout.addLayout(header_layout)

        # --- CONTENT SPLIT ---
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)
        
        # ==========================================
        # LEFT COLUMN (Overview & Recent Activity)
        # ==========================================
        left_col = QVBoxLayout()
        left_col.setSpacing(20)

        # 1. TOP METRICS ROW (Three Separate Cards)
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16) # Gap between the cards

        # --- A. Available Funds ---
        self.card_avail = QFrame()
        self.card_avail.setStyleSheet("""
            QFrame {
                background-color: rgba(108, 92, 231, 0.65);
                border-top: 1.5px solid rgba(255, 255, 255, 0.6);
                border-left: 1.5px solid rgba(255, 255, 255, 0.4);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            QLabel { border: none; background: transparent; }
        """)
        avail_layout = QVBoxLayout(self.card_avail)
        avail_layout.setContentsMargins(20, 20, 20, 20)
        
        avail_title = QLabel("Available Funds")
        avail_title.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-weight: bold; font-size: 12px; text-transform: uppercase;")
        self.lbl_avail_val = QLabel("₱ 0.00")
        self.lbl_avail_val.setStyleSheet("color: #FFFFFF; font-size: 26px; font-weight: bold;")
        
        avail_layout.addWidget(avail_title)
        avail_layout.addWidget(self.lbl_avail_val)
        avail_layout.addStretch()

        # --- B. Total Collected ---
        self.card_in = QFrame()
        self.card_in.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.55);
                border-top: 1.5px solid rgba(255, 255, 255, 0.9);
                border-left: 1.5px solid rgba(255, 255, 255, 0.7);
                border-bottom: 1px solid rgba(255, 255, 255, 0.3);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 16px;
            }
            QLabel { border: none; background: transparent; }
        """)
        in_layout = QVBoxLayout(self.card_in)
        in_layout.setContentsMargins(20, 20, 20, 20)
        
        in_title = QLabel("Total Collected")
        in_title.setStyleSheet("color: #8A8A9E; font-weight: bold; font-size: 12px; text-transform: uppercase;")
        self.lbl_in_val = QLabel("₱ 0.00")
        self.lbl_in_val.setStyleSheet("color: #1A1A3E; font-size: 26px; font-weight: bold;")
        
        in_layout.addWidget(in_title)
        in_layout.addWidget(self.lbl_in_val)
        in_layout.addStretch()

        # --- C. Total Expenses ---
        self.card_out = QFrame()
        self.card_out.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.55);
                border-top: 1.5px solid rgba(255, 255, 255, 0.9);
                border-left: 1.5px solid rgba(255, 255, 255, 0.7);
                border-bottom: 1px solid rgba(255, 255, 255, 0.3);
                border-right: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 16px;
            }
            QLabel { border: none; background: transparent; }
        """)
        out_layout = QVBoxLayout(self.card_out)
        out_layout.setContentsMargins(20, 20, 20, 20)
        
        out_title = QLabel("Total Expenses")
        out_title.setStyleSheet("color: #8A8A9E; font-weight: bold; font-size: 12px; text-transform: uppercase;")
        self.lbl_out_val = QLabel("₱ 0.00")
        self.lbl_out_val.setStyleSheet("color: #1A1A3E; font-size: 26px; font-weight: bold;")
        
        out_layout.addWidget(out_title)
        out_layout.addWidget(self.lbl_out_val)
        out_layout.addStretch()

        metrics_layout.addWidget(self.card_avail, stretch=1)
        metrics_layout.addWidget(self.card_in, stretch=1)
        metrics_layout.addWidget(self.card_out, stretch=1)

        left_col.addLayout(metrics_layout)

        # 2. SEPARATE CHART CARD
        self.card_chart = QFrame()
        self.card_chart.setStyleSheet("""
            QFrame {
                background-color: rgba(108, 92, 231, 0.65);
                border-top: 1.5px solid rgba(255, 255, 255, 0.6);
                border-left: 1.5px solid rgba(255, 255, 255, 0.4);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 16px;
            }
            QLabel { border: none; background: transparent; }
        """)
        chart_layout = QVBoxLayout(self.card_chart)
        chart_layout.setContentsMargins(24, 20, 24, 20)
        
        self.chart = MiniChart([], line_color="#FFFFFF") 
        chart_layout.addWidget(self.chart)
        
        lbl_disclaimer = QLabel("* Financial metrics and chart reflect Approved & Active transactions only.")
        lbl_disclaimer.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 11px;")
        chart_layout.addWidget(lbl_disclaimer)
        
        left_col.addWidget(self.card_chart)

        # 2. Recent Transactions Table Card
        self.card_recent = QFrame()
        self.card_recent.setObjectName("profilePanel")
        recent_layout = QVBoxLayout(self.card_recent)
        recent_layout.setContentsMargins(20, 20, 20, 20)
        
        recent_title = QLabel("Recent Activity")
        recent_title.setStyleSheet("color: #1A1A3E; font-size: 16px; font-weight: bold;")
        recent_layout.addWidget(recent_title)
        
        self.table_recent = QTableWidget()
        self.table_recent.setObjectName("modernTable")
        self.table_recent.setColumnCount(4)
        self.table_recent.setHorizontalHeaderLabels(["Date", "Type", "Amount", "Status"])
        self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_recent.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_recent.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_recent.setShowGrid(False)
        self.table_recent.verticalHeader().setVisible(False)
        
        recent_layout.addWidget(self.table_recent)
        left_col.addWidget(self.card_recent, stretch=1)

        # ==========================================
        # RIGHT COLUMN (Status & Buckets)
        # ==========================================
        right_col = QVBoxLayout()
        right_col.setSpacing(20)

        # 3. Collection & Inventory Status Card
        self.card_status = QFrame()
        self.card_status.setObjectName("profilePanel")
        status_layout = QVBoxLayout(self.card_status)
        status_layout.setContentsMargins(20, 20, 20, 20)
        
        stat_title = QLabel("Collection Status")
        stat_title.setStyleSheet("color: #1A1A3E; font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        status_layout.addWidget(stat_title)
        
        self.prog_collection = QProgressBar()
        self.prog_collection.setStyleSheet("""
            QProgressBar { border-radius: 4px; background-color: #EEF0F8; border: none; }
            QProgressBar::chunk { border-radius: 4px; background-color: #6C5CE7; }
        """)
        self.prog_collection.setTextVisible(False)
        self.prog_collection.setFixedHeight(8)
        status_layout.addWidget(self.prog_collection)
        
        status_metrics = QHBoxLayout()
        self.lbl_paid_count = QLabel("0 Paid")
        self.lbl_paid_count.setStyleSheet("color: #6C5CE7; font-weight: bold;")
        self.lbl_pending_count = QLabel("0 Pending")
        self.lbl_pending_count.setStyleSheet("color: #FD79A8; font-weight: bold;")
        
        status_metrics.addWidget(self.lbl_paid_count)
        status_metrics.addStretch()
        status_metrics.addWidget(self.lbl_pending_count)
        status_layout.addLayout(status_metrics)
        
        status_layout.addSpacing(15)
        
        inv_title = QLabel("Assets & Inventory")
        inv_title.setStyleSheet("color: #1A1A3E; font-size: 16px; font-weight: bold;")
        status_layout.addWidget(inv_title)
        
        self.lbl_inv_count = QLabel("0 Total Items Logged")
        self.lbl_inv_count.setStyleSheet("color: #9B9BB0; font-size: 14px;")
        status_layout.addWidget(self.lbl_inv_count)
        
        right_col.addWidget(self.card_status)

        # 4. Fund Buckets Utilization List
        self.card_buckets = QFrame()
        self.card_buckets.setObjectName("profilePanel")
        buckets_wrapper_layout = QVBoxLayout(self.card_buckets)
        buckets_wrapper_layout.setContentsMargins(20, 20, 20, 20)
        
        buckets_title = QLabel("Fund Utilization")
        buckets_title.setStyleSheet("color: #1A1A3E; font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        buckets_wrapper_layout.addWidget(buckets_title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QWidget#scrollContainer { background: transparent; }")
        
        self.buckets_container = QWidget()
        self.buckets_container.setObjectName("scrollContainer")
        self.buckets_layout = QVBoxLayout(self.buckets_container)
        self.buckets_layout.setContentsMargins(0,0,0,0)
        self.buckets_layout.setSpacing(16)
        self.buckets_layout.addStretch()
        
        scroll.setWidget(self.buckets_container)
        buckets_wrapper_layout.addWidget(scroll)
        
        right_col.addWidget(self.card_buckets, stretch=1)

        content_layout.addLayout(left_col, stretch=18)
        content_layout.addLayout(right_col, stretch=10)
        main_layout.addLayout(content_layout)
        
        self._apply_glow(self.card_avail)
        self._apply_glow(self.card_in)
        self._apply_glow(self.card_out)
        self._apply_glow(self.card_chart)
        self._apply_glow(self.card_recent)
        self._apply_glow(self.card_status)
        self._apply_glow(self.card_buckets)

    def load_plans(self):
        try:
            plans = list_budget_plans()
            current_id = self.combo_plan.currentData()
            
            self.combo_plan.blockSignals(True)
            self.combo_plan.clear()
            
            for p in plans:
                if isinstance(p, dict):
                    self.combo_plan.addItem(f"Plan {p.get('plan_id')} ({p.get('academic_year')} Sem {p.get('semester')})", p.get("plan_id"))
            
            if current_id:
                idx = self.combo_plan.findData(current_id)
                self.combo_plan.setCurrentIndex(idx if idx >= 0 else self.combo_plan.count() - 1)
            else:
                self.combo_plan.setCurrentIndex(self.combo_plan.count() - 1)
                
            self.combo_plan.blockSignals(False)
            self.refresh_dashboard()
            
        except Exception as e:
            print(f"Error loading plans: {e}")

    def refresh_dashboard(self):
        try:
            plan_id = self.combo_plan.currentData()
            if not plan_id:
                return

            data = get_dashboard_summary(plan_id)
            all_transactions = list_transactions()
            
            plan = data.get("active_plan")
            if plan:
                self.lbl_subtitle.setText(f"Total Plan Budget: ₱{float(plan.get('total_planned_budget', 0)):,.2f}")

            totals = data.get("totals", {})
            self.lbl_avail_val.setText(f"₱ {float(totals.get('available_funds', 0)):,.2f}")
            self.lbl_in_val.setText(f"₱ {float(totals.get('payments', 0)):,.2f}")
            self.lbl_out_val.setText(f"₱ {float(totals.get('expenses', 0)):,.2f}")
            
            backend_cash_flow = data.get("cash_flow", [])
            self.chart.update_data(backend_cash_flow)

            coll = data.get("collection_progress", {})
            paid = coll.get('paid_count', 0)
            pending = coll.get('pending_count', 0)
            total_students = paid + pending
            
            self.lbl_paid_count.setText(f"{paid} Paid")
            self.lbl_pending_count.setText(f"{pending} Pending")
            
            if total_students > 0:
                self.prog_collection.setValue(int((paid / total_students) * 100))
            else:
                self.prog_collection.setValue(0)
                
            inv = data.get("inventory_summary", {})
            self.lbl_inv_count.setText(f"{inv.get('total_items', 0)} Unique Items ({inv.get('total_quantity', 0)} Qty)")

            self.update_recent_transactions(all_transactions, plan_id)
            self.update_buckets(data.get("fund_bucket_utilization", []))
            
        except Exception as e:
            print(f"Dashboard Sync Error: {e}")

    def update_recent_transactions(self, transactions, current_plan_id):
        plan_txns = [t for t in transactions if str(t.get('plan_id')) == str(current_plan_id)]
        recent = sorted(plan_txns, key=lambda x: x.get('transaction_id', 0), reverse=True)[:8]
        
        self.table_recent.setRowCount(0)
        for row, t in enumerate(recent):
            self.table_recent.insertRow(row)
            
            date_str = str(t.get("transaction_date", ""))[:10]
            tx_type = str(t.get("transaction_type", ""))
            amount = f"₱ {float(t.get('amount') or 0):,.2f}"
            status = str(t.get("approval_status", ""))
            
            self.table_recent.setItem(row, 0, QTableWidgetItem(date_str))
            
            type_item = QTableWidgetItem(tx_type)
            if tx_type == "PAYMENT":
                type_item.setForeground(QColor("#00B894")) 
            else:
                type_item.setForeground(QColor("#FD79A8")) 
            self.table_recent.setItem(row, 1, type_item)
            
            self.table_recent.setItem(row, 2, QTableWidgetItem(amount))
            
            status_item = QTableWidgetItem(status)
            if status == "Pending":
                status_item.setForeground(QColor("#E65100")) # Orange for pending warning
            self.table_recent.setItem(row, 3, status_item)

    def update_buckets(self, buckets_data):
        while self.buckets_layout.count() > 1:
            item = self.buckets_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not buckets_data:
            empty_lbl = QLabel("No buckets allocated for this plan.")
            empty_lbl.setStyleSheet("color: #9B9BB0;")
            self.buckets_layout.insertWidget(0, empty_lbl)
            return

        colors = [
            "QProgressBar::chunk { border-radius: 4px; background-color: #6C5CE7; }", 
            "QProgressBar::chunk { border-radius: 4px; background-color: #FD79A8; }", 
            "QProgressBar::chunk { border-radius: 4px; background-color: #00B894; }"  
        ]

        for i, b in enumerate(buckets_data):
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 10)
            layout.setSpacing(4)
            
            title_row = QHBoxLayout()
            name = QLabel(b.get("bucket_name", "Unknown"))
            name.setStyleSheet("color: #1A1A3E; font-weight: 600; font-size: 13px;")
            
            spent = float(b.get("spent_amount", 0))
            planned = float(b.get("planned_amount", 0))
            percent = int((spent / planned * 100)) if planned > 0 else 0
            
            vals = QLabel(f"₱{spent:,.0f} / ₱{planned:,.0f}")
            vals.setStyleSheet("color: #9B9BB0; font-size: 12px;")
            
            title_row.addWidget(name)
            title_row.addStretch()
            title_row.addWidget(vals)
            
            prog = QProgressBar()
            base_css = "QProgressBar { border-radius: 4px; background-color: #EEF0F8; border: none; } "
            prog.setStyleSheet(base_css + colors[i % len(colors)])
            prog.setTextVisible(False)
            prog.setFixedHeight(6)
            prog.setMaximum(100)
            prog.setValue(min(percent, 100))
            
            layout.addLayout(title_row)
            layout.addWidget(prog)
            
            self.buckets_layout.insertWidget(self.buckets_layout.count() - 1, container)