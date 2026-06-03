import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.services.student_service import list_students, create_student, update_student, delete_student

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QMessageBox, 
    QComboBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt

class StudentsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("contentArea")
        self.current_student_id = None 
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(24)

        # main table (needs rework) ---------------------------
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        
        title = QLabel("Student Directory")
        title.setObjectName("pageTitle")
        left_col.addWidget(title)

        self.table = QTableWidget()
        self.table.setObjectName("modernTable")
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Name", "Program", "Role", "Approve", "Status"
        ])
        self.table.setColumnHidden(6, True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False) 
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self.on_table_select)
        
        left_col.addWidget(self.table)
        
        # form panel (reworking soon)
        right_panel = QFrame()
        right_panel.setObjectName("profilePanel")
        right_panel.setFixedWidth(300)
        
        panel_layout = QVBoxLayout(right_panel)
        panel_layout.setContentsMargins(24, 32, 24, 32)
        panel_layout.setSpacing(16)
        
        avatar_layout = QVBoxLayout()
        avatar_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        self.avatar_circle = QLabel("🙍‍♂️")
        self.avatar_circle.setObjectName("profileAvatar")
        self.avatar_circle.setFixedSize(70, 70)
        self.avatar_circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.profile_name = QLabel("New Student")
        self.profile_name.setObjectName("profileName")
        self.profile_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        avatar_layout.addWidget(self.avatar_circle)
        avatar_layout.addWidget(self.profile_name)
        panel_layout.addLayout(avatar_layout)
        
        # form fields
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(12)
        
        self.input_id = QLineEdit()
        self.input_id.setPlaceholderText("202X-XXXX")
        self.input_name = QLineEdit()
        self.input_program = QLineEdit()
        
        self.input_year = QComboBox()
        self.input_year.addItems(["1", "2", "3", "4", "5", "6"])
        
        self.input_role = QLineEdit()
        self.input_approve = QCheckBox("Can Approve")
        
        self.input_status = QComboBox()
        self.input_status.addItems(["Active", "Inactive", "Alumni"])

        # styling for inputs
        for inp in [self.input_id, self.input_name, self.input_program, self.input_role, self.input_year, self.input_status]:
            inp.setObjectName("formInput")

        form_layout.addRow("ID", self.input_id)
        form_layout.addRow("Name", self.input_name)
        form_layout.addRow("Program", self.input_program)
        form_layout.addRow("Year", self.input_year)
        form_layout.addRow("Role", self.input_role)
        form_layout.addRow("", self.input_approve)
        form_layout.addRow("Status", self.input_status)
        
        panel_layout.addLayout(form_layout)
        panel_layout.addStretch()
        
        # buttons ----------------
        self.btn_save = QPushButton("Save Student")
        self.btn_save.setObjectName("primaryBtn")
        self.btn_save.clicked.connect(self.save_student)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self.clear_form)
        
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setObjectName("dangerBtn")
        self.btn_delete.clicked.connect(self.delete_student)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.btn_clear)
        btn_row.addWidget(self.btn_delete)

        panel_layout.addWidget(self.btn_save)
        panel_layout.addLayout(btn_row)

        main_layout.addLayout(left_col, stretch=1)
        main_layout.addWidget(right_panel)

    def load_data(self):
        self.table.setRowCount(0) 
        try:
            students = list_students()
            for row_idx, student in enumerate(students):
                self.table.insertRow(row_idx)
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(student.get("student_id", ""))))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(student.get("name", ""))))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(student.get("program", ""))))
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(student.get("role_title", ""))))
                self.table.setItem(row_idx, 4, QTableWidgetItem("Yes" if student.get("can_approve") else "No"))
                self.table.setItem(row_idx, 5, QTableWidgetItem(str(student.get("status", "Active"))))
                
                year_item = QTableWidgetItem(str(student.get("year_level", "")))
                self.table.setItem(row_idx, 6, year_item) 
        except Exception as e:
            print(f"Error loading students: {e}")

    def on_table_select(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        self.current_student_id = self.table.item(row, 0).text()
        student_name = self.table.item(row, 1).text()
        
        # Update Profile Header
        self.profile_name.setText(student_name)
        initials = "".join([w[0] for w in student_name.split()[:2]]).upper() if student_name else "ID"
        self.avatar_circle.setText(initials)
        
        # Fill Form
        self.input_id.setText(self.current_student_id)
        self.input_id.setReadOnly(True)
        self.input_name.setText(student_name)
        self.input_program.setText(self.table.item(row, 2).text())
        
        role_text = self.table.item(row, 3).text()
        self.input_role.setText(role_text if role_text != "None" else "")
        self.input_approve.setChecked(self.table.item(row, 4).text() == "Yes")
        self.input_status.setCurrentText(self.table.item(row, 5).text())
        
        # check for the hidden year column
        year_item = self.table.item(row, 6)
        if year_item and year_item.text():
            self.input_year.setCurrentText(year_item.text())
        else:
            self.input_year.setCurrentIndex(0)

    def clear_form(self):
        self.current_student_id = None
        self.profile_name.setText("New Student")
        self.avatar_circle.setText("NEW")
        self.input_id.clear()
        self.input_id.setReadOnly(False) 
        self.input_name.clear()
        self.input_program.clear()
        self.input_year.setCurrentIndex(0)
        self.input_role.clear()
        self.input_approve.setChecked(False)
        self.input_status.setCurrentIndex(0)
        self.table.clearSelection()

    def save_student(self):
        student_id = self.input_id.text().strip()
        name = self.input_name.text().strip()
        
        if not student_id or not name:
            QMessageBox.warning(self, "Validation Error", "Student ID and Name are required!")
            return
            
        data = {
            "student_id": student_id,
            "name": name,
            "program": self.input_program.text().strip() or None,
            "year_level": int(self.input_year.currentText()),
            "role_title": self.input_role.text().strip() or None,
            "can_approve": self.input_approve.isChecked(),
            "status": self.input_status.currentText()
        }
        
        try:
            if self.current_student_id:
                update_student(self.current_student_id, data)
            else:
                create_student(data)
                
            self.clear_form()
            self.load_data() 
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))

    def delete_student(self):
        if not self.current_student_id: return
        reply = QMessageBox.question(self, "Confirm", f"Delete {self.current_student_id}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_student(self.current_student_id)
                self.clear_form()
                self.load_data()
            except Exception as e:
                pass