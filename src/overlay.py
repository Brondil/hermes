"""PyQt6 overlay window for PoE2 Rumor Counter."""
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class OverlayWindow(QMainWindow):
    """Transparent counter overlay on top of everything."""

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.85)
        # Optional: let clicks pass through the window background
        # We enable click-through via a custom paintEvent in main.py if needed

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.right() - 200, 20, 190, 60)

        self.label_count = QLabel("Rumors: 0")
        self.label_count.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self._apply_inactive_style()

        layout = QVBoxLayout()
        layout.addWidget(self.label_count, alignment=Qt.AlignmentFlag.AlignCenter)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def set_count(self, value: int):
        self.label_count.setText(f"Rumors: {value}")

    def show_active(self):
        self._apply_active_style()

    def show_inactive(self):
        self._apply_inactive_style()

    def _apply_active_style(self):
        self.label_count.setStyleSheet(
            "color: #00ff00; "
            "background-color: rgba(30, 30, 30, 180); "
            "border-radius: 8px; "
            "padding: 8px 16px;"
        )

    def _apply_inactive_style(self):
        self.label_count.setStyleSheet(
            "color: #cccccc; "
            "background-color: rgba(30, 30, 30, 150); "
            "border-radius: 8px; "
            "padding: 8px 16px;"
        )

    def _resize_grip(self):
        """Allow dragging by label."""
        pass  # Handled by mouse events in main.py