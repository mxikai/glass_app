import sys
import os

# --- THE MASTER BRIDGE ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.report_service import get_report_data, generate_report_pdf
from backend.services.budget_service import list_budget_plans
# -------------------------

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QComboBox, QFrame, QListWidget, 
    QTextBrowser, QFileDialog, QMessageBox, QListWidgetItem,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class ReportsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        self.plans_data = []
        
        self.report_types = {
            "Transparency Summary": "transparency",
            "Budget Plan Details": "budget-plan",
            "Fee Collection Progress": "collection",
            "Expense Liquidation": "expense",
            "Inventory & Assets": "inventory"
        }

        self.setup_ui()

    def showEvent(self, event):
        """Refreshes the plans and preview every time the tab is clicked."""
        super().showEvent(event)
        self.load_all_data()

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
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(24)

        # ==========================================
        # LEFT COLUMN (Controls & Selection)
        # ==========================================
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        
        title = QLabel("Reports & Analytics")
        title.setObjectName("pageTitle")
        
        subtitle = QLabel("Generate, preview, and export official organization documents.")
        subtitle.setStyleSheet("color: #9B9BB0; font-size: 13px; margin-bottom: 8px;")
        
        left_col.addWidget(title)
        left_col.addWidget(subtitle)

        self.left_card = QFrame()
        self.left_card.setObjectName("profilePanel")
        left_card_layout = QVBoxLayout(self.left_card)
        left_card_layout.setContentsMargins(24, 24, 24, 24)
        left_card_layout.setSpacing(16)

        # Plan Selector
        self.lbl_plan = QLabel("Select Budget Plan:")
        self.lbl_plan.setStyleSheet("font-weight: 700; color: #1A1A3E; font-size: 14px; font-family: 'Segoe UI';")
        
        self.input_plan = QComboBox()
        self.input_plan.setObjectName("formInput")
        self.input_plan.currentIndexChanged.connect(self.refresh_preview)
        
        left_card_layout.addWidget(self.lbl_plan)
        left_card_layout.addWidget(self.input_plan)

        # Report Type List
        self.lbl_type = QLabel("Select Report Type:")
        self.lbl_type.setStyleSheet("font-weight: 700; color: #1A1A3E; font-size: 14px; font-family: 'Segoe UI'; margin-top: 12px;")
        
        self.list_reports = QListWidget()
        self.list_reports.setStyleSheet("""
            QListWidget {
                border: none;
                background-color: transparent;
                outline: none;
            }
            QListWidget::item {
                padding: 14px 16px;
                color: #9B9BB0;
                border-radius: 10px;
                margin-bottom: 4px;
                font-family: 'Segoe UI';
                font-size: 14px;
                font-weight: 600;
            }
            QListWidget::item:selected {
                background-color: #F5F3FF;
                color: #6C5CE7;
            }
            QListWidget::item:hover:!selected {
                background-color: #F9FAFC;
                color: #1A1A3E;
            }
        """)
        
        for name in self.report_types.keys():
            item = QListWidgetItem(name)
            self.list_reports.addItem(item)
            
        self.list_reports.setCurrentRow(0)
        self.list_reports.itemSelectionChanged.connect(self.refresh_preview)
        
        left_card_layout.addWidget(self.lbl_type)
        left_card_layout.addWidget(self.list_reports)
        
        left_col.addWidget(self.left_card, stretch=1)
        
        # ==========================================
        # RIGHT COLUMN (Preview & Export Panel)
        # ==========================================
        self.right_panel = QFrame()
        self.right_panel.setObjectName("profilePanel")
        
        panel_layout = QVBoxLayout(self.right_panel)
        panel_layout.setContentsMargins(32, 32, 32, 32)
        panel_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        self.panel_title = QLabel("Report Preview")
        self.panel_title.setObjectName("panelTitle")
        self.panel_title.setStyleSheet("font-size: 20px;")
        
        self.btn_export = QPushButton("Download PDF")
        self.btn_export.setObjectName("primaryBtn")
        self.btn_export.setFixedWidth(160)
        self.btn_export.clicked.connect(self.export_pdf)
        
        header_layout.addWidget(self.panel_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_export)
        
        panel_layout.addLayout(header_layout)

        # Document Preview Area
        self.preview_area = QTextBrowser()
        self.preview_area.setStyleSheet("""
            QTextBrowser {
                background-color: #FFFFFF;
                border: 2px solid #EEF0F8;
                border-radius: 16px;
                padding: 30px;
                color: #1A1A3E;
            }
        """)
        panel_layout.addWidget(self.preview_area)

        main_layout.addLayout(left_col, stretch=1)
        main_layout.addWidget(self.right_panel, stretch=2)
        
        self._apply_glow(self.right_panel)

    def load_all_data(self):
        try:
            self.plans_data = list_budget_plans()
            self.input_plan.blockSignals(True)
            self.input_plan.clear()
            
            for p in self.plans_data:
                if isinstance(p, dict):
                    self.input_plan.addItem(f"Plan {p.get('plan_id')} ({p.get('academic_year')} Sem {p.get('semester')})", p.get("plan_id"))
                    
            self.input_plan.blockSignals(False)
            self.refresh_preview()
            
        except Exception as e:
            QMessageBox.warning(self, "Data Error", f"Could not load plans: {e}")

    def refresh_preview(self):
        plan_id = self.input_plan.currentData()
        selected_items = self.list_reports.selectedItems()
        
        if not plan_id or not selected_items:
            self.preview_area.setHtml("<h3 style='color:#9B9BB0; text-align:center; font-family: Segoe UI;'><br><br><br>Select a budget plan and report type to view the preview.</h3>")
            self.btn_export.setEnabled(False)
            return

        report_name = selected_items[0].text()
        backend_type = self.report_types.get(report_name)
        
        self.panel_title.setText(f"{report_name}")
        self.btn_export.setEnabled(True)

        try:
            data = get_report_data(backend_type, plan_id)
            html_content = self.generate_html_preview(backend_type, data)
            self.preview_area.setHtml(html_content)
        except Exception as e:
            self.preview_area.setHtml(f"<h3 style='color:#FD79A8; font-family: Segoe UI;'>Error generating preview:</h3><p style='color:#1A1A3E;'>{str(e)}</p>")
            self.btn_export.setEnabled(False)

    def export_pdf(self):
        plan_id = self.input_plan.currentData()
        selected_items = self.list_reports.selectedItems()
        
        if not plan_id or not selected_items:
            return
            
        report_name = selected_items[0].text()
        backend_type = self.report_types.get(report_name)
        
        default_filename = f"GLASS_{backend_type.capitalize()}_Plan{plan_id}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Report as PDF", 
            default_filename, 
            "PDF Files (*.pdf)"
        )
        
        if file_path:
            try:
                pdf_bytes = generate_report_pdf(backend_type, plan_id)
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)
                QMessageBox.information(self, "Success", f"Report saved successfully to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to generate PDF:\n{str(e)}")


    # ==========================================
    # HTML PREVIEW GENERATION & MODULAR RENDERING
    # ==========================================
    def _get_css(self):
        return """
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; color: #1A1A3E; line-height: 1.5; }
            h2 { color: #1A1A3E; font-size: 24px; font-weight: 700; margin-bottom: 5px; }
            hr { border: 0; border-top: 2px solid #EEF0F8; margin-bottom: 20px; }
            h3 { color: #6C5CE7; font-size: 16px; margin-top: 30px; margin-bottom: 10px; font-weight: 700; border-bottom: 2px solid #EEF0F8; padding-bottom: 5px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; }
            th { background-color: #F5F3FF; color: #6C5CE7; text-align: left; padding: 12px; font-size: 13px; font-weight: 700; border-bottom: 2px solid #E4E6F1; }
            td { border-bottom: 1px solid #EEF0F8; padding: 12px; font-size: 13px; color: #1A1A3E; }
            p { font-size: 14px; color: #4A4A68; }
            .metric-box { background-color: #F9FAFC; border: 1px solid #EEF0F8; padding: 16px; margin-bottom: 16px; border-radius: 12px; }
            .metric-title { font-size: 12px; color: #9B9BB0; text-transform: uppercase; font-weight: bold; margin-bottom: 4px; }
            .metric-value { font-size: 20px; color: #1A1A3E; font-weight: bold; margin-top: 0; }
            .badge { background-color: #EDE7F6; color: #6C5CE7; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; }
        </style>
        """

    def generate_html_preview(self, r_type, data):
        html = self._get_css()
        
        title_str = data.get('report_type', r_type).replace('-', ' ').title()
        if r_type == "transparency":
            title_str = "Master Transparency (Combined Report)"
            
        html += f"<h2>GLASS Official {title_str}</h2><hr>"
        
        plan = data.get("plan", {}) or data.get("budget_plan", {}).get("plan", {})
        if plan:
            html += f"<p><b>Academic Year:</b> {plan.get('academic_year')} &nbsp;|&nbsp; <b>Semester:</b> {plan.get('semester')} &nbsp;|&nbsp; <b>Plan ID:</b> {plan.get('plan_id')}</p>"

        if r_type == "transparency":
            html += self._render_summary_boxes(data.get("dashboard_summary", {}))
            html += self._render_budget_plan(data.get("budget_plan", {}))
            html += self._render_collection(data.get("collection", {}))
            html += self._render_expense(data.get("expense", {}))
            html += self._render_inventory(data.get("inventory", {}))
            
        elif r_type == "budget-plan":
            html += self._render_budget_plan(data)
        elif r_type == "collection":
            html += self._render_collection(data)
        elif r_type == "expense":
            html += self._render_expense(data)
        elif r_type == "inventory":
            html += self._render_inventory(data)

        return html

    def _render_summary_boxes(self, summary):
        if not summary: return ""
        totals = summary.get("totals", {})
        coll = summary.get("collection_progress", {})
        
        html = "<h3>Financial Overview</h3>"
        html += "<table style='border: none;'><tr>"
        html += f"<td style='border: none; width: 33%;'><div class='metric-box'><p class='metric-title'>Total Collected</p><p class='metric-value'>₱{float(totals.get('payments') or 0):,.2f}</p></div></td>"
        html += f"<td style='border: none; width: 33%;'><div class='metric-box'><p class='metric-title'>Total Expenses</p><p class='metric-value'>₱{float(totals.get('expenses') or 0):,.2f}</p></div></td>"
        html += f"<td style='border: none; width: 33%;'><div class='metric-box'><p class='metric-title'>Available Funds</p><p class='metric-value' style='color:#00B894;'>₱{float(totals.get('available_funds') or 0):,.2f}</p></div></td>"
        html += "</tr></table>"
        
        html += "<h3>Collection Status</h3>"
        html += "<table style='border: none;'><tr>"
        html += f"<td style='border: none; width: 50%;'><div class='metric-box'><p class='metric-title'>Students Fully Paid</p><p class='metric-value'>{coll.get('paid_count', 0)}</p></div></td>"
        html += f"<td style='border: none; width: 50%;'><div class='metric-box'><p class='metric-title'>Students Pending</p><p class='metric-value' style='color:#FD79A8;'>{coll.get('pending_count', 0)}</p></div></td>"
        html += "</tr></table>"
        return html

    def _render_budget_plan(self, data):
        if not data: return ""
        plan = data.get("plan", {})
        
        html = "<table style='border: none;'><tr>"
        html += f"<td style='border: none; width: 50%;'><div class='metric-box'><p class='metric-title'>Total Planned Budget</p><p class='metric-value'>₱{float(plan.get('total_planned_budget') or 0):,.2f}</p></div></td>"
        html += f"<td style='border: none; width: 50%;'><div class='metric-box'><p class='metric-title'>Semestral Fee Per Student</p><p class='metric-value'>₱{float(plan.get('semestral_fee_amount') or 0):,.2f}</p></div></td>"
        html += "</tr></table>"
        
        html += "<h3>Fund Buckets Allocation</h3><table><tr><th>ID</th><th>Bucket Name</th><th>Allocation Amount</th></tr>"
        for b in data.get("fund_buckets", []):
            html += f"<tr><td>{b.get('bucket_id')}</td><td><b>{b.get('bucket_name')}</b></td><td>₱{float(b.get('planned_amount') or 0):,.2f}</td></tr>"
        if not data.get("fund_buckets"): html += "<tr><td colspan='3'>No buckets configured.</td></tr>"
        html += "</table>"
        
        html += "<h3>Specific Budget Items</h3><table><tr><th>ID</th><th>Item Name</th><th>Type</th><th>Allocation</th></tr>"
        for i in data.get("budget_items", []):
            html += f"<tr><td>{i.get('budget_item_id')}</td><td>{i.get('item_name')}</td><td><span class='badge'>{i.get('item_type')}</span></td><td>₱{float(i.get('planned_amount') or 0):,.2f}</td></tr>"
        if not data.get("budget_items"): html += "<tr><td colspan='4'>No items configured.</td></tr>"
        html += "</table>"
        return html

    def _render_collection(self, data):
        if not data: return ""
        html = "<h3>Paid Students Roster</h3><table><tr><th>Student ID</th><th>Name</th><th>Payment Count</th></tr>"
        for s in data.get("paid_students", []):
            html += f"<tr><td>{s.get('student_id')}</td><td><b>{s.get('name')}</b></td><td>{len(s.get('payments', []))} recorded</td></tr>"
        if not data.get("paid_students"): html += "<tr><td colspan='3'>No paid students in this plan.</td></tr>"
        html += "</table>"
        
        html += "<h3>Pending Students</h3><table><tr><th>Student ID</th><th>Name</th><th>Status</th></tr>"
        for s in data.get("pending_students", []):
            html += f"<tr><td>{s.get('student_id')}</td><td>{s.get('name')}</td><td><span class='badge' style='background-color:#FCE4EC; color:#FD79A8;'>Pending</span></td></tr>"
        if not data.get("pending_students"): html += "<tr><td colspan='3'>No pending students.</td></tr>"
        html += "</table>"
        return html

    def _render_expense(self, data):
        if not data: return ""
        html = "<h3>Organization Expenses</h3><table><tr><th>Date</th><th>Budget Item</th><th>Line Items (Qty x Item @ Cost)</th><th>Amount Spent</th></tr>"
        for e in data.get("expenses", []):
            date = str(e.get('transaction_date', ''))[:10]
            html += f"<tr><td>{date}</td><td><b>{e.get('budget_item_name')}</b></td><td style='color:#6C5CE7;'>{e.get('line_item_summary')}</td><td><b>₱{float(e.get('amount') or 0):,.2f}</b></td></tr>"
        if not data.get("expenses"): html += "<tr><td colspan='4'>No expenses recorded.</td></tr>"
        html += "</table>"
        return html

    def _render_inventory(self, data):
        if not data: return ""
        html = "<h3>Physical Assets & Inventory</h3><table><tr><th>Item Name</th><th>Acquisition Source</th><th>Quantity</th><th>Unit Cost</th><th>Condition</th></tr>"
        for i in data.get("inventory_items", []):
            source = "Legacy" if i.get('source_type') == 'Legacy' else f"Txn #{i.get('transaction_id')}"
            html += f"<tr><td><b>{i.get('item_name')}</b></td><td>{source}</td><td>{i.get('quantity')}</td><td>₱{float(i.get('unit_cost') or 0):,.2f}</td><td><span class='badge'>{i.get('item_condition')}</span></td></tr>"
        if not data.get("inventory_items"): html += "<tr><td colspan='5'>No inventory assets recorded.</td></tr>"
        html += "</table>"
        return html