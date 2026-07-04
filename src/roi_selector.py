from PyQt6.QtWidgets import QWidget, QRubberBand, QApplication
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QSize
from PyQt6.QtGui import QColor

class ROIDialog(QWidget):
    selection_complete = pyqtSignal(QRect)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._origin = None
        self._rubber_band = None

    def start_selection(self):
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._origin = event.pos()
            self._rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self._rubber_band.setGeometry(QRect(self._origin, QSize()))
            self._rubber_band.show()

    def mouseMoveEvent(self, event):
        if self._rubber_band:
            self._rubber_band.setGeometry(QRect(self._origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._rubber_band:
            final_rect = self._rubber_band.geometry().normalized()
            self._rubber_band.hide()
            self.selection_complete.emit(final_rect)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
