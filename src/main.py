import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt

from src.config import Config
from src.hotkey import GlobalHotkeyManager
from src.roi_selector import ROIDialog
from src.scanner import ScannerWorker

class MainApplication(QMainWindow):
    """Main Window for PoE2 Rumor Counter."""

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.scanner_worker = ScannerWorker()
        self.hotkey_manager = GlobalHotkeyManager(self)
        
        # UI Setup
        self.setWindowTitle("PoE2 Rumor Counter - Menu")
        self.setFixedSize(300, 400)
        
        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # --- Status Indicator (Counter Label) ---
        self.counter_label = QLabel("Слухи: 0")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: white;
                background-color: #333;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        layout.addWidget(self.counter_label)

        # --- Control Buttons ---
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Select ROI & Start")
        self.start_btn.clicked.connect(self.start_roi_selection)
        btn_layout.addWidget(self.start_btn)

        self.toggle_session_btn = QPushButton("F8: Stop")
        self.toggle_session_btn.setEnabled(False)
        # Note: F8 is handled via GlobalHotkeyManager, but we keep the button for UI control
        self.toggle_session_btn.clicked.connect(self.on_ui_toggle_requested)
        btn_layout.addWidget(self.toggle_session_btn)
        
        layout.addLayout(btn_layout)

        # --- Info Area (Last Detected Rumor) ---
        self.last_rumor_label = QLabel("Последний слух: —")
        self.last_rumor_label.setWordWrap(True)
        self.last_rumor_label.setStyleSheet("color: #aaa; font-style: italic;")
        layout.addWidget(self.last_rumor_label)

    def _setup_connections(self):
        # Worker -> UI (Thread-safe via signals)
        self.scanner_worker.count_changed.connect(self.update_ui_counter)
        self.scanner_worker.rumor_found.connect(self.update_last_rumor)
        self.scanner_worker.error_occurred.connect(self.on_error)

    # --- UI Logic ---
    def update_ui_counter(self, count):
        self.counter_label.setText(f"Слухи: {count}")
        self.counter_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: white;
                background-color: #2E7D32;  /* Green when active */
                border-radius: 10px;
                padding: 20px;
            }
        """)

    def update_last_rumor(self, text):
        self.last_rumor_label.setText(f"Последний слух: {text}")

    def on_error(self, error_msg):
        self.last_rumor_label.setText(f"Ошибка: {error_msg}")
        # Auto-stop scanner if we hit a fatal error
        if self.scanner_worker.isRunning():
            self.on_session_stop()

    def on_ui_toggle_requested(self):
        """Triggered by the UI button."""
        if self.scanner_worker.is_running:
            self.on_session_stop()
        else:
            # If they weren't in a session, maybe they want to start? 
            # But usually Start requires ROI selection first.
            pass

    def on_session_start(self):
        """Called when scanning begins."""
        self.toggle_session_btn.setText("F8: Stop")
        self.toggle_session_btn.setEnabled(True)
        self.last_rumor_label.setText("Scanning active...")

    def on_session_stop(self):
        """Called when scanning stops."""
        self.scanner_worker.stop()
        self.toggle_session_btn.setText("F8: Start")
        self.toggle_session_btn.setEnabled(True)
        self.counter_label.setStyleSheet("""
            QLabel {
                font-size: 48px;
                font-weight: bold;
                color: white;
                background-color: #333;
                border-radius: 10px;
                padding: 20px;
            }
        """)

    def start_roi_selection(self):
        """Launches the UI to draw ROI area."""
        self.selector = ROIDialog()
        self.selector.selection_complete.connect(self.apply_roi)
        self.selector.start_selection()

    def apply_roi(self, rect):
        """Callback when user finishes drawing ROI."""
        print(f"Applied ROI: {rect}")
        # Pass the raw QRect to scanner for setup
        self.scanner_worker.set_roi(rect)
        # Start the worker thread
        if not self.scanner_worker.isRunning():
            self.scanner_worker.start()
        
        self.on_session_start()

    def notify_stop_via_hotkey(self):
        """Callback for GlobalHotkeyManager when F8 is pressed."""
        if self.scanner_worker.is_running:
            self.on_session_stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainApplication()
    window.show()
    sys.exit(app.exec())
