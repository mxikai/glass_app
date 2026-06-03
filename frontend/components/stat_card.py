from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StatCard(QWidget):
    """Compact summary card: icon + value + label."""

    def __init__(self, icon: str, value: str, label: str, accent: str = "#6C5CE7", parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setFixedHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("cardIcon")
        icon_lbl.setStyleSheet(f"font-size: 20px; color: {accent};")

        self.value_lbl = QLabel(value)
        self.value_lbl.setObjectName("cardValue")

        self.label_lbl = QLabel(label)
        self.label_lbl.setObjectName("cardLabel")

        layout.addWidget(icon_lbl)
        layout.addWidget(self.value_lbl)
        layout.addWidget(self.label_lbl)

    def set_value(self, value: str):
        self.value_lbl.setText(value)


class BucketProgressCard(QWidget):
    """Fund bucket card with progress bar."""

    def __init__(self, icon: str, title: str, subtitle: str,
                 progress: int, progress_label: str,
                 days_left: str = "", color: str = "purple", parent=None):
        super().__init__(parent)
        self.setObjectName("bucketCard")
        self.setMinimumHeight(140)

        from PyQt6.QtWidgets import QProgressBar
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        # Header row
        header = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 22px;")

        dots = QLabel("···")
        dots.setStyleSheet("color: #C5BFEE; font-size: 18px;")
        dots.setAlignment(Qt.AlignmentFlag.AlignRight)

        header.addWidget(icon_lbl)
        header.addStretch()
        header.addWidget(dots)
        layout.addLayout(header)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("bucketTitle")

        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("bucketSub")

        layout.addWidget(title_lbl)
        layout.addWidget(sub_lbl)
        layout.addStretch()

        # Progress row
        prog_row = QHBoxLayout()
        prog_lbl = QLabel("Progress")
        prog_lbl.setObjectName("bucketSub")
        pct_lbl = QLabel(progress_label)
        pct_lbl.setObjectName("bucketSub")
        pct_lbl.setStyleSheet("color: #1A1A3E; font-weight: 600;")
        prog_row.addWidget(prog_lbl)
        prog_row.addStretch()
        prog_row.addWidget(pct_lbl)
        layout.addLayout(prog_row)

        bar = QProgressBar()
        color_map = {
            "purple": "bucketProgress",
            "pink":   "bucketProgressPink",
            "green":  "bucketProgressGreen",
        }
        bar.setObjectName(color_map.get(color, "bucketProgress"))
        bar.setRange(0, 100)
        bar.setValue(progress)
        bar.setTextVisible(False)
        bar.setFixedHeight(7)
        layout.addWidget(bar)

        # Footer
        footer = QHBoxLayout()
        detail_lbl = QLabel(subtitle)
        detail_lbl.setObjectName("bucketSub")

        if days_left:
            days_badge = QLabel(days_left)
            pill_colors = {
                "purple": ("EDE7F6", "6C5CE7"),
                "pink":   ("FCE4EC", "E91E63"),
                "green":  ("E8F5E9", "2E7D32"),
            }
            bg, fg = pill_colors.get(color, ("EDE7F6", "6C5CE7"))
            days_badge.setStyleSheet(
                f"background:#{bg}; color:#{fg}; border-radius:8px;"
                f"padding:2px 8px; font-size:11px; font-family:'Segoe UI';"
            )
            footer.addStretch()
            footer.addWidget(days_badge)

        layout.addLayout(footer)
