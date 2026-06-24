import sys
import os
from datetime import date

# --- THE MASTER BRIDGE ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.inventory_service import (
    list_inventory_items, create_inventory_item, update_inventory_item, delete_inventory_item
)
from backend.services.transaction_service import list_transactions
# -------------------------

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, 
    QComboBox, QFrame, QSpinBox, QDoubleSpinBox,
    QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class InventoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        
        self.current_item_id = None
        self.inventory_data = []
        self.expense_txns = []

        # --- PAGINATION TRACKERS ---
        self.current_page = 1
        self.items_per_page = 50

        self.setup_ui()
        self.load_all_data()

    def showEvent(self, event):
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
        # LEFT COLUMN (Main Table)
        # ==========================================
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        
        # --- HEADER WITH YEAR FILTER ---
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("Inventory Tracker")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Inventory items are physical assets connected to expense transactions or legacy inherited items.")
        subtitle.setStyleSheet("color: #9B9BB0; font-size: 13px; margin-bottom: 8px;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        lbl_filter = QLabel("Filter by Year:")
        lbl_filter.setStyleSheet("font-weight: 600; color: #9B9BB0; font-size: 13px; font-family: 'Segoe UI';")
        self.filter_year_cb = QComboBox()
        self.filter_year_cb.setObjectName("formInput")
        self.filter_year_cb.setFixedWidth(120)
        self.filter_year_cb.currentIndexChanged.connect(self.on_filter_changed)
        
        header_layout.addWidget(lbl_filter)
        header_layout.addWidget(self.filter_year_cb)
        
        left_col.addLayout(header_layout)
        # ------------------------------------

        self.table = QTableWidget()
        self.table.setObjectName("modernTable")
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Source", "Item Name", "Qty", "Cost", "Condition", "Status", "Date Recorded"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.on_table_select)
        
        left_col.addWidget(self.table)
        
        # --- PAGINATION CONTROLS ---
        pagination_layout = QHBoxLayout()
        
        self.btn_prev = QPushButton("◄ Prev")
        self.btn_prev.setObjectName("secondaryBtn")
        self.btn_prev.setFixedWidth(80)
        self.btn_prev.clicked.connect(self.prev_page)
        
        self.lbl_page = QLabel("Page 1 of 1")
        self.lbl_page.setStyleSheet("color: #9B9BB0; font-weight: bold;")
        
        self.btn_next = QPushButton("Next ►")
        self.btn_next.setObjectName("secondaryBtn")
        self.btn_next.setFixedWidth(80)
        self.btn_next.clicked.connect(self.next_page)
        
        pagination_layout.addWidget(self.btn_prev)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.lbl_page)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_next)
        
        left_col.addLayout(pagination_layout)
        # ---------------------------
        
        # ==========================================
        # RIGHT COLUMN (Form Panel)
        # ==========================================
        self.right_panel = QFrame()
        self.right_panel.setObjectName("profilePanel")
        self.right_panel.setFixedWidth(400) 
        
        panel_layout = QVBoxLayout(self.right_panel)
        panel_layout.setContentsMargins(24, 32, 24, 32)
        panel_layout.setSpacing(16)
        
        form_title = QLabel("Inventory Item")
        form_title.setObjectName("panelTitle")
        form_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(form_title)
        
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        
        self.input_id = QLineEdit()
        self.input_id.setReadOnly(True)
        self.input_id.setPlaceholderText("Auto-generated")
        self.input_id.setStyleSheet("background-color: #F5F6FA; color: #9B9BB0;")
        
        self.input_source = QComboBox()
        self.input_source.addItems(["Purchase", "Legacy"])
        self.input_source.currentTextChanged.connect(self.on_source_changed)

        self.lbl_txn = QLabel("Expense Txn *")
        self.input_txn = QComboBox()
        self.input_txn.currentIndexChanged.connect(self.on_txn_selected)
        
        self.lbl_note = QLabel("Source Note *")
        self.input_note = QLineEdit()
        self.input_note.setPlaceholderText("e.g. Handed down from 2024 admins")
        
        self.input_name = QLineEdit()
        
        self.input_qty = QSpinBox()
        self.input_qty.setRange(1, 999999)
        
        self.input_cost = QDoubleSpinBox()
        self.input_cost.setRange(0, 9999999.99)
        self.input_cost.setPrefix("₱ ")
        
        self.input_condition = QComboBox()
        self.input_condition.addItems(["New", "Good", "Fair", "Damaged"])
        
        self.input_status = QComboBox()
        self.input_status.addItems(["Available", "In Use", "Lost", "Disposed", "Active"])
        
        self.input_date = QLineEdit()
        self.input_date.setPlaceholderText("YYYY-MM-DD")
        self.input_date.setText(str(date.today()))

        for inp in [self.input_id, self.input_source, self.input_txn, self.input_note, 
                    self.input_name, self.input_qty, self.input_cost, self.input_condition, 
                    self.input_status, self.input_date]:
            inp.setObjectName("formInput")

        form_layout.addRow("Inventory ID", self.input_id)
        form_layout.addRow("Source Type", self.input_source)
        form_layout.addRow(self.lbl_txn, self.input_txn)
        form_layout.addRow(self.lbl_note, self.input_note)
        form_layout.addRow("Item Name *", self.input_name)
        form_layout.addRow("Quantity", self.input_qty)
        form_layout.addRow("Unit Cost", self.input_cost)
        form_layout.addRow("Condition", self.input_condition)
        form_layout.addRow("Status", self.input_status)
        form_layout.addRow("Date Recorded", self.input_date)
        
        panel_layout.addLayout(form_layout)
        panel_layout.addStretch()
        
        self.btn_save = QPushButton("Save Inventory Item")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self.save_item)
        
        self.btn_clear = QPushButton("New")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self.clear_form)
        
        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self.delete_item)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_delete)

        panel_layout.addWidget(self.btn_save)
        panel_layout.addLayout(btn_row)

        main_layout.addLayout(left_col, stretch=1)
        main_layout.addWidget(self.right_panel)

        self.on_source_changed("Purchase")
        
        self._apply_glow(self.right_panel)

    # --- Interaction Logic ---
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_table()

    def next_page(self):
        self.current_page += 1
        self.refresh_table()

    def on_filter_changed(self):
        self.current_page = 1 # Reset to page 1 when filter changes!
        self.refresh_table()

    def on_source_changed(self, source_type):
        is_purchase = (source_type == "Purchase")
        self.lbl_txn.setVisible(is_purchase)
        self.input_txn.setVisible(is_purchase)
        self.lbl_note.setVisible(not is_purchase)
        self.input_note.setVisible(not is_purchase)

    # --- Data Logic ---
    def load_all_data(self):
        try:
            self.inventory_data = list_inventory_items()
            all_transactions = list_transactions()
            self.expense_txns = [t for t in all_transactions if t.get("transaction_type") == "EXPENSE"]
            
            self.populate_dropdowns()
            self.refresh_table()
        except Exception as e:
            QMessageBox.warning(self, "Data Error", f"Could not load data: {e}")

    def populate_dropdowns(self):
        # 1. Populate Expense Transactions
        curr_txn_data = self.input_txn.currentData()
        self.input_txn.blockSignals(True)
        self.input_txn.clear()
        self.input_txn.addItem("-- Select Expense Item --", None)
        
        for tx in self.expense_txns:
            txn_id = tx.get("transaction_id")
            line_items = tx.get("line_items", [])
            
            if not line_items:
                label = f"Txn #{txn_id} - ₱{float(tx.get('amount') or 0):,.2f}"
                self.input_txn.addItem(label, (txn_id, None, "", 1, 0.0))
            else:
                for li in line_items:
                    li_id = li.get("line_item_id")
                    name = li.get("item_name", "")
                    qty = li.get("quantity", 1)
                    cost = float(li.get("unit_cost") or 0.0)
                    
                    label = f"Txn #{txn_id}: {name} (x{qty})"
                    self.input_txn.addItem(label, (txn_id, li_id, name, qty, cost))
                    
        if curr_txn_data:
            for i in range(self.input_txn.count()):
                if self.input_txn.itemData(i) == curr_txn_data:
                    self.input_txn.setCurrentIndex(i)
                    break
        self.input_txn.blockSignals(False)

        # 2. Populate the Year Filter
        self.filter_year_cb.blockSignals(True)
        current_year = self.filter_year_cb.currentText()
        self.filter_year_cb.clear()
        self.filter_year_cb.addItem("All Years", None)
        
        years = set()
        for item in self.inventory_data:
            date_rec = str(item.get("date_recorded", ""))
            if len(date_rec) >= 4:
                years.add(date_rec[:4])
                
        for y in sorted(list(years), reverse=True):
            self.filter_year_cb.addItem(y, y)
            
        idx = self.filter_year_cb.findText(current_year)
        if idx >= 0:
            self.filter_year_cb.setCurrentIndex(idx)
        self.filter_year_cb.blockSignals(False)

    def on_txn_selected(self, index):
        if index < 0: return
        data = self.input_txn.itemData(index)
        if data:
            txn_id, li_id, name, qty, cost = data
            if name:
                self.input_name.setText(name)
            if qty:
                self.input_qty.setValue(int(qty))
            if cost:
                self.input_cost.setValue(float(cost))

    def refresh_table(self):
        self.table.setRowCount(0) 
        
        filter_year = self.filter_year_cb.currentData()
        filtered_data = self.inventory_data
        
        if filter_year:
            filtered_data = [item for item in filtered_data if str(item.get("date_recorded", "")).startswith(filter_year)]

        # --- PAGINATION LOGIC ---
        total_items = len(filtered_data)
        total_pages = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
        if self.current_page > total_pages: self.current_page = max(1, total_pages)
        
        self.lbl_page.setText(f"Page {self.current_page} of {total_pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)
        
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_data = filtered_data[start_idx:end_idx]
        # ------------------------

        for row_idx, item in enumerate(page_data):
            self.table.insertRow(row_idx)
            
            s_type = str(item.get("source_type", "Purchase"))
            if s_type == "Purchase":
                source_display = f"Txn #{item.get('transaction_id', '')}"
            else:
                source_display = "Legacy"

            self.table.setItem(row_idx, 0, QTableWidgetItem(str(item.get("inventory_item_id", ""))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(source_display))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(item.get("item_name", ""))))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(item.get("quantity", 1))))
            self.table.setItem(row_idx, 4, QTableWidgetItem(f"₱{float(item.get('unit_cost') or 0):,.2f}"))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(item.get("item_condition", ""))))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(item.get("status", "Active"))))
            
            raw_date = str(item.get("date_recorded", ""))
            clean_date = raw_date[:10] if raw_date else "Unknown"
            self.table.setItem(row_idx, 7, QTableWidgetItem(clean_date))

    def on_table_select(self):
        rows = self.table.selectedItems()
        if not rows: return
        
        self.current_item_id = int(self.table.item(rows[0].row(), 0).text())
        
        target_item = None
        for item in self.inventory_data:
            if isinstance(item, dict) and str(item.get("inventory_item_id")) == str(self.current_item_id):
                target_item = item
                break
                
        if target_item:
            self.input_id.setText(str(target_item.get("inventory_item_id", "")))
            self.input_source.setCurrentText(target_item.get("source_type", "Purchase"))
            
            target_txn_id = target_item.get("transaction_id")
            target_li_id = target_item.get("expense_line_item_id")
            
            self.input_txn.blockSignals(True)
            idx_txn = -1
            for i in range(self.input_txn.count()):
                data = self.input_txn.itemData(i)
                if data and data[0] == target_txn_id and data[1] == target_li_id:
                    idx_txn = i
                    break
            
            if idx_txn == -1 and target_txn_id: 
                for i in range(self.input_txn.count()):
                    data = self.input_txn.itemData(i)
                    if data and data[0] == target_txn_id:
                        idx_txn = i
                        break
                        
            if idx_txn >= 0:
                self.input_txn.setCurrentIndex(idx_txn)
            self.input_txn.blockSignals(False)
                
            self.input_note.setText(target_item.get("source_note", ""))
            self.input_name.setText(target_item.get("item_name", ""))
            self.input_qty.setValue(int(target_item.get("quantity") or 1))
            self.input_cost.setValue(float(target_item.get("unit_cost") or 0))
            self.input_condition.setCurrentText(target_item.get("item_condition", "New"))
            self.input_status.setCurrentText(target_item.get("status", "Available"))
            
            raw_date = str(target_item.get("date_recorded", ""))
            self.input_date.setText(raw_date[:10] if raw_date else str(date.today()))

    def clear_form(self):
        self.current_item_id = None
        self.input_id.clear()
        self.input_source.setCurrentIndex(0)
        self.input_txn.setCurrentIndex(0)
        self.input_note.clear()
        self.input_name.clear()
        self.input_qty.setValue(1)
        self.input_cost.setValue(0.0)
        self.input_condition.setCurrentIndex(0)
        self.input_status.setCurrentIndex(0)
        self.input_date.setText(str(date.today()))
        self.table.clearSelection()

    def save_item(self):
        source_type = self.input_source.currentText()
        
        txn_data = self.input_txn.currentData()
        txn_id = txn_data[0] if txn_data else None
        li_id = txn_data[1] if txn_data else None
        
        name = self.input_name.text().strip()
        note = self.input_note.text().strip()
        
        if source_type == "Purchase" and not txn_id:
            QMessageBox.warning(self, "Validation Error", "You must select a source Expense Transaction.")
            return
        if source_type == "Legacy" and not note:
            QMessageBox.warning(self, "Validation Error", "Source Note is required for Legacy items.")
            return
        if not name:
            QMessageBox.warning(self, "Validation Error", "Item Name is required.")
            return
            
        data = {
            "source_type": source_type,
            "transaction_id": txn_id if source_type == "Purchase" else None,
            "expense_line_item_id": li_id if source_type == "Purchase" else None,
            "source_note": note if source_type == "Legacy" else "",
            "item_name": name,
            "quantity": self.input_qty.value(),
            "unit_cost": self.input_cost.value(),
            "item_condition": self.input_condition.currentText(),
            "status": self.input_status.currentText(),
            "date_recorded": self.input_date.text().strip()
        }
        
        try:
            if self.current_item_id:
                update_inventory_item(self.current_item_id, data)
            else:
                create_inventory_item(data)
                
            self.load_all_data()
            self.clear_form()
            QMessageBox.information(self, "Success", "Inventory item saved successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Database Error", str(e))

    def delete_item(self):
        if not self.current_item_id:
            QMessageBox.warning(self, "Selection Error", "Please select an item to delete.")
            return
            
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     "Are you sure you want to delete this inventory record?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_inventory_item(self.current_item_id)
                self.load_all_data()
                self.clear_form()
            except Exception as e:
                QMessageBox.critical(self, "Delete Error", str(e))