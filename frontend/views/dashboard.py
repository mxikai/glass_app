import sys
import os

#THIS ALL NEEDS REWORKING 

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.budget_service import list_budget_plans
from backend.services.transaction_service import list_transactions

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QProgressBar, QLineEdit,
    QSizePolicy, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QPolygonF
from PyQt6.QtCore import QPointF
import math


class MiniChart(QWidget):
    def __init__(self, data: list, color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self.data = data
        self.color = QColor(color)
        self.setMinimumHeight(60)

    def paintEvent(self, event):
        if not self.data:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        mn, mx = min(self.data), max(self.data)
        rng = mx - mn or 1
        pad = 8

        def pt(i, v):
            x = pad + (i / (len(self.data) - 1)) * (w - 2 * pad)
            y = h - pad - ((v - mn) / rng) * (h - 2 * pad)
            return QPointF(x, y)

        pts = [pt(i, v) for i, v in enumerate(self.data)]

        # Fill area
        fill_color = QColor(self.color)
        fill_color.setAlpha(40)
        poly = QPolygonF([QPointF(pts[0].x(), h), *pts, QPointF(pts[-1].x(), h)])
        painter.setBrush(fill_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(poly)

        # Line
        pen = QPen(self.color, 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i], pts[i + 1])

        # Highlight last point
        painter.setBrush(self.color)
        painter.setPen(QPen(QColor("white"), 2))
        last = pts[-1]
        painter.drawEllipse(last, 5, 5)


class BudgetBarChart(QWidget):
    def __init__(self, data: list, parent=None):
        """data = [(label, used, total), ...]"""
        super().__init__(parent)
        self.data = data
        self.setMinimumHeight(len(data) * 36 + 16)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        row_h = h / len(self.data)
        bar_h = 8
        label_w = 120
        bar_w = w - label_w - 60

        colors = ["#6C5CE7", "#FD79A8", "#00B894", "#FDCB6E", "#74B9FF"]

        for i, (label, used, total) in enumerate(self.data):
            y_center = i * row_h + row_h / 2

            # Label
            painter.setPen(QColor("#1A1A3E"))
            font = painter.font()
            font.setFamily("Segoe UI")
            font.setPointSize(9)
            painter.setFont(font)
            painter.drawText(0, int(y_center - 6), label_w, 20, Qt.AlignmentFlag.AlignVCenter, label)

            # Background bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#EEF0F8"))
            bar_x = label_w
            bar_y = int(y_center - bar_h / 2)
            painter.drawRoundedRect(bar_x, bar_y, int(bar_w), bar_h, 4, 4)

            # Filled portion
            fill = int(bar_w * min(used / total, 1.0)) if total > 0 else 0
            painter.setBrush(QColor(colors[i % len(colors)]))
            painter.drawRoundedRect(bar_x, bar_y, fill, bar_h, 4, 4)

            # Percentage
            pct = f"{int(used / total * 100)}%" if total > 0 else "0%"
            painter.setPen(QColor("#9B9BB0"))
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(bar_x + int(bar_w) + 6, int(y_center - 6), 50, 20, Qt.AlignmentFlag.AlignVCenter, pct)


# ── Dashboard page ────────────────────────────────────────────────────────────
class DashboardView(QWidget):
    # Mock data
    MOCK = {
        "semester": "1st Semester AY 2025–2026",
        "plan_status": "Approved",
        "total_budget": "₱25,000.00",
        "collected": "₱18,750.00",
        "expenses": "₱11,200.00",
        "balance": "₱7,550.00",
        "pending_payments": 12,
        "pending_txns": 3,
        "member_count": 100,
        "semestral_fee": "₱250.00",
        "chart_data": [40, 65, 55, 80, 70, 90, 75, 95, 88, 100],
        "buckets": [
            ("Events",     11200, 15000),
            ("Supplies",   3400,  5000),
            ("Operations", 1800,  3000),
            ("Emergency",  0,     2000),
        ],
        "recent_payments": [
            ("Kotomi T.", "2024-0001", "₱250", "Paid"),
            ("Jun Reyes",  "2024-0042", "₱250", "Paid"),
            ("Maria Cruz", "2024-0078", "₱250", "Pending"),
            ("Rico Lim",   "2024-0093", "₱250", "Paid"),
            ("Ana Santos", "2024-0112", "₱250", "Pending"),
        ],
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        self._fetch_initial_data()
        self._build_ui()
        self.setup_auto_update()

    def _fetch_initial_data(self):
        try:
            plans = list_budget_plans()
            txns = list_transactions()
            
            if plans:
                active_plans = [p for p in plans if p.get("status") == "Active"]
                current_plan = active_plans[-1] if active_plans else plans[-1]
                plan_id = current_plan.get("plan_id")
                
                # Update Semester & Total Budget
                real_budget = float(current_plan.get("total_planned_budget") or 0)
                self.MOCK["total_budget"] = f"₱{real_budget:,.2f}"
                self.MOCK["semester"] = f"{current_plan.get('semester', '')} Sem {current_plan.get('academic_year', '')}"
                
                # Process Transactions for the Chart and Balances
                plan_txns = [t for t in txns if t.get("plan_id") == plan_id and t.get("transaction_status") != "Void"]
                plan_txns.sort(key=lambda x: x.get("transaction_date", "")) # Sort chronologically
                
                collected = 0.0
                expenses = 0.0
                running_balance = 0.0
                chart_data = [0.0] # Chart starts at 0
                
                for t in plan_txns:
                    amt = float(t.get("amount") or 0)
                    if t.get("transaction_type") == "PAYMENT":
                        collected += amt
                        running_balance += amt
                    elif t.get("transaction_type") == "EXPENSE":
                        expenses += amt
                        running_balance -= amt
                    
                    chart_data.append(running_balance)
                
                # If there are no transactions yet, make a flat line so it doesn't crash
                if len(chart_data) == 1:
                    chart_data.append(0.0)
                    
                # Save calculated data
                self.MOCK["collected"] = f"₱{collected:,.2f}"
                self.MOCK["expenses"] = f"₱{expenses:,.2f}"
                self.MOCK["balance"] = f"₱{(collected - expenses):,.2f}"
                self.MOCK["chart_data"] = chart_data
                
        except Exception as e:
            print(f"Backend connection error: {e}")

    def setup_auto_update(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_budget_data)
        self.refresh_timer.start(5000)

    def refresh_budget_data(self):
        try:
            self._fetch_initial_data()
    
            for chart in self.findChildren(MiniChart):
                chart.data = self.MOCK["chart_data"]
                chart.update()
            
            overview_labels = [l for l in self.findChildren(QLabel) if l.objectName() == "overviewValue"]
            if len(overview_labels) >= 3:
                overview_labels[0].setText(self.MOCK["total_budget"])
                overview_labels[1].setText(self.MOCK["collected"])
                overview_labels[2].setText(self.MOCK["balance"])
                
            card_labels = [l for l in self.findChildren(QLabel) if l.objectName() == "cardValue"]
            if len(card_labels) >= 4:
                card_labels[0].setText(self.MOCK["total_budget"])
                card_labels[1].setText(self.MOCK["collected"])
                card_labels[2].setText(self.MOCK["expenses"])
                card_labels[3].setText(self.MOCK["balance"])
                
        except Exception as e:
            pass

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("contentArea")
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # ── Header ────────────────────────────────────────────
        header_row = QHBoxLayout()
        title_col = QVBoxLayout()
        subtitle = QLabel("Primary")
        subtitle.setObjectName("pageSubtitle")
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        title_col.addWidget(subtitle)
        title_col.addWidget(title)
        title_col.setSpacing(0)

        search = QLineEdit()
        search.setObjectName("searchBar")
        search.setPlaceholderText("🔍  Search students, transactions…")
        search.setFixedWidth(260)
        search.setFixedHeight(38)

        sem_badge = QLabel(f"  {self.MOCK['semester']}  ")
        sem_badge.setStyleSheet(
            "background: white; color: #6C5CE7; border-radius: 10px;"
            "font-size: 11px; font-family: 'Segoe UI'; padding: 4px 10px;"
        )

        header_row.addLayout(title_col)
        header_row.addStretch()
        header_row.addWidget(sem_badge)
        header_row.addSpacing(12)
        header_row.addWidget(search)
        layout.addLayout(header_row)

        # ── Summary stat cards ─────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)
        stat_data = [
            ("💰", self.MOCK["total_budget"],  "Total Budget",     "#6C5CE7"),
            ("✅", self.MOCK["collected"],      "Collected",        "#00B894"),
            ("📤", self.MOCK["expenses"],       "Expenses",         "#FD79A8"),
            ("💵", self.MOCK["balance"],        "Balance",          "#FDCB6E"),
            ("⏳", str(self.MOCK["pending_payments"]), "Pending Payments", "#E17055"),
            ("🔄", str(self.MOCK["pending_txns"]),     "Pending Txns",     "#74B9FF"),
        ]
        for icon, val, lbl, accent in stat_data:
            card = self._stat_card(icon, val, lbl, accent)
            cards_row.addWidget(card)
        layout.addLayout(cards_row)

        # ── Main row: overview chart + right panel ─────────────
        main_row = QHBoxLayout()
        main_row.setSpacing(18)

        # Left: overview card + bucket cards
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        left_col.addWidget(self._overview_card())
        left_col.addWidget(self._buckets_section())

        # Right panel
        right_panel = self._right_panel()
        right_panel.setFixedWidth(260)

        main_row.addLayout(left_col, stretch=3)
        main_row.addWidget(right_panel, stretch=0)
        layout.addLayout(main_row)

        layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ── Card builders ─────────────────────────────────────────
    def _stat_card(self, icon, value, label, accent):
        card = QWidget()
        card.setObjectName("statCard")
        card.setFixedHeight(95)
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(2)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 18px; color: {accent};")
        val_lbl = QLabel(value)
        val_lbl.setObjectName("cardValue")
        val_lbl.setStyleSheet(f"font-size: 17px; font-weight: 700; color: #1A1A3E;")
        lbl_lbl = QLabel(label)
        lbl_lbl.setObjectName("cardLabel")

        v.addWidget(icon_lbl)
        v.addWidget(val_lbl)
        v.addWidget(lbl_lbl)
        return card

    def _overview_card(self):
        card = QWidget()
        card.setObjectName("overviewCard")
        card.setMinimumHeight(200)

        outer = QVBoxLayout(card)
        outer.setContentsMargins(22, 18, 22, 14)
        outer.setSpacing(8)

        # Top row
        top = QHBoxLayout()
        title = QLabel("Budget Overview")
        title.setObjectName("overviewTitle")
        combo = QPushButton("This Semester  ▾")
        combo.setStyleSheet(
            "background: rgba(255,255,255,0.18); color: rgba(255,255,255,0.85);"
            "border-radius: 8px; border: none; font-size: 11px;"
            "padding: 4px 10px; font-family: 'Segoe UI';"
        )
        top.addWidget(title)
        top.addStretch()
        top.addWidget(combo)
        outer.addLayout(top)

        # Chart
        chart = MiniChart(self.MOCK["chart_data"], color="#ffffff")
        chart.setMinimumHeight(90)
        outer.addWidget(chart)

        # Bottom stats row
        bottom = QHBoxLayout()
        bottom.setSpacing(24)
        stats = [
            ("Total Budget",    self.MOCK["total_budget"]),
            ("Collected",       self.MOCK["collected"]),
            ("Remaining",       self.MOCK["balance"]),
        ]
        for lbl, val in stats:
            col = QVBoxLayout()
            col.setSpacing(0)
            l = QLabel(lbl)
            l.setObjectName("overviewSub")
            v = QLabel(val)
            v.setObjectName("overviewValue")
            v.setStyleSheet("font-size: 14px; font-weight: 700; color: white;")
            col.addWidget(l)
            col.addWidget(v)
            bottom.addLayout(col)
        bottom.addStretch()
        outer.addLayout(bottom)

        return card

    def _buckets_section(self):
        section = QWidget()
        section.setObjectName("contentArea")
        v = QVBoxLayout(section)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)

        hdr = QHBoxLayout()
        title = QLabel("Fund Bucket Utilization")
        title.setObjectName("sectionHeader")
        hdr.addWidget(title)
        hdr.addStretch()
        v.addLayout(hdr)

        # Chart card
        chart_card = QWidget()
        chart_card.setObjectName("statCard")
        chart_card.setMinimumHeight(160)
        cl = QVBoxLayout(chart_card)
        cl.setContentsMargins(18, 16, 18, 16)

        chart = BudgetBarChart(self.MOCK["buckets"])
        cl.addWidget(chart)
        v.addWidget(chart_card)

        # Three bucket cards in a row
        row = QHBoxLayout()
        row.setSpacing(14)
        bucket_cards = [
            ("🎉", "Events Fund",       "₱11,200 / ₱15,000", 75, "75%", "Active",   "purple"),
            ("📝", "Supplies Fund",      "₱3,400 / ₱5,000",   68, "68%", "Active",   "pink"),
            ("⚙️", "Operations Fund",    "₱1,800 / ₱3,000",   60, "60%", "Active",   "green"),
        ]
        for icon, title_t, sub, prog, prog_lbl, days, color in bucket_cards:
            bc = self._bucket_card(icon, title_t, sub, prog, prog_lbl, days, color)
            row.addWidget(bc)
        v.addLayout(row)

        return section

    def _bucket_card(self, icon, title, subtitle, progress, prog_lbl, badge, color):
        card = QWidget()
        card.setObjectName("bucketCard")
        card.setMinimumHeight(145)
        v = QVBoxLayout(card)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(4)

        top = QHBoxLayout()
        icon_l = QLabel(icon)
        icon_l.setStyleSheet("font-size: 20px;")
        dots = QLabel("···")
        dots.setStyleSheet("color: #C5BFEE; font-size: 16px;")
        top.addWidget(icon_l)
        top.addStretch()
        top.addWidget(dots)
        v.addLayout(top)

        t = QLabel(title)
        t.setObjectName("bucketTitle")
        s = QLabel(subtitle)
        s.setObjectName("bucketSub")
        v.addWidget(t)
        v.addWidget(s)
        v.addStretch()

        prog_row = QHBoxLayout()
        pl = QLabel("Progress")
        pl.setObjectName("bucketSub")
        pv = QLabel(prog_lbl)
        pv.setStyleSheet("color: #1A1A3E; font-weight: 600; font-size: 11px; font-family:'Segoe UI';")
        prog_row.addWidget(pl)
        prog_row.addStretch()
        prog_row.addWidget(pv)
        v.addLayout(prog_row)

        bar = QProgressBar()
        color_map = {"purple": "bucketProgress", "pink": "bucketProgressPink", "green": "bucketProgressGreen"}
        bar.setObjectName(color_map.get(color, "bucketProgress"))
        bar.setRange(0, 100)
        bar.setValue(progress)
        bar.setTextVisible(False)
        bar.setFixedHeight(7)
        v.addWidget(bar)

        badge_colors = {
            "purple": ("#EDE7F6", "#6C5CE7"),
            "pink":   ("#FCE4EC", "#C2185B"),
            "green":  ("#E8F5E9", "#2E7D32"),
        }
        bg, fg = badge_colors.get(color, ("#EDE7F6", "#6C5CE7"))
        b = QLabel(f"  {badge}  ")
        b.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:8px;"
            f"padding:2px 6px; font-size:10px; font-family:'Segoe UI';"
        )
        b.setAlignment(Qt.AlignmentFlag.AlignRight)
        v.addWidget(b, alignment=Qt.AlignmentFlag.AlignRight)

        return card

    def _right_panel(self):
        panel = QWidget()
        panel.setObjectName("rightPanel")
        v = QVBoxLayout(panel)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(14)

        # Recent Payments section
        hdr = QHBoxLayout()
        title = QLabel("Recent Payments")
        title.setObjectName("panelTitle")
        view_all = QPushButton("View All")
        view_all.setObjectName("viewAllBtn")
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(view_all)
        v.addLayout(hdr)

        for name, sid, amount, status in self.MOCK["recent_payments"]:
            row = self._payment_row(name, sid, amount, status)
            v.addWidget(row)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #EEF0F8;")
        v.addWidget(line)

        # Collection progress
        coll_title = QLabel("Collection Progress")
        coll_title.setObjectName("panelTitle")
        v.addWidget(coll_title)

        coll_pct = int(18750 / 25000 * 100)
        coll_bar = QProgressBar()
        coll_bar.setObjectName("bucketProgress")
        coll_bar.setRange(0, 100)
        coll_bar.setValue(coll_pct)
        coll_bar.setTextVisible(False)
        coll_bar.setFixedHeight(9)
        v.addWidget(coll_bar)

        coll_detail = QLabel(f"₱18,750 collected of ₱25,000  ({coll_pct}%)")
        coll_detail.setObjectName("cardLabel")
        coll_detail.setWordWrap(True)
        v.addWidget(coll_detail)

        # Members
        mem_title = QLabel("Members")
        mem_title.setObjectName("panelTitle")
        v.addWidget(mem_title)

        mem_row = QHBoxLayout()
        for initials, color in [("KT","#6C5CE7"),("JR","#FD79A8"),("MC","#00B894"),("RL","#FDCB6E")]:
            av = QLabel(initials)
            av.setFixedSize(32, 32)
            av.setAlignment(Qt.AlignmentFlag.AlignCenter)
            av.setStyleSheet(
                f"background:{color}22; color:{color}; border-radius:16px;"
                f"font-size:10px; font-weight:700; font-family:'Segoe UI';"
            )
            mem_row.addWidget(av)
        more = QLabel(f"+{self.MOCK['member_count'] - 4}")
        more.setFixedSize(32, 32)
        more.setAlignment(Qt.AlignmentFlag.AlignCenter)
        more.setStyleSheet(
            "background:#EEF0F8; color:#9B9BB0; border-radius:16px;"
            "font-size:10px; font-family:'Segoe UI';"
        )
        mem_row.addWidget(more)
        mem_row.addStretch()
        v.addLayout(mem_row)

        v.addStretch()
        return panel

    def _payment_row(self, name, student_id, amount, status):
        row = QWidget()
        row.setObjectName("studentRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(10)

        # Avatar
        initials = "".join(w[0] for w in name.split()[:2]).upper()
        av = QLabel(initials)
        av.setFixedSize(32, 32)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av.setStyleSheet(
            "background:#EDE7F6; color:#6C5CE7; border-radius:16px;"
            "font-size:10px; font-weight:700; font-family:'Segoe UI';"
        )

        info = QVBoxLayout()
        info.setSpacing(0)
        n = QLabel(name)
        n.setObjectName("studentName")
        sid = QLabel(student_id)
        sid.setObjectName("studentDetail")
        info.addWidget(n)
        info.addWidget(sid)

        badge_map = {
            "Paid":    ("badgePaid",    "#E8F5E9", "#2E7D32"),
            "Pending": ("badgePending", "#FFF3E0", "#E65100"),
        }
        _, bg, fg = badge_map.get(status, ("badgePaid", "#EDE7F6", "#6C5CE7"))
        badge = QLabel(status)
        badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:8px;"
            f"padding:2px 8px; font-size:10px; font-family:'Segoe UI';"
        )

        amt = QLabel(amount)
        amt.setStyleSheet("font-size:12px; font-weight:600; color:#1A1A3E; font-family:'Segoe UI';")

        h.addWidget(av)
        h.addLayout(info)
        h.addStretch()
        h.addWidget(amt)
        h.addWidget(badge)
        return row
