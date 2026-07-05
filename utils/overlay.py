"""
Overlay Module — TopMost + ClickThrough counter overlay for PoE2 Rumor Tracker.
Показывает «Слухи: X» поверх окна игры, мышь проходит сквозь оверлей.
ТЗ п.3.1
"""

import sys
import ctypes
from typing import Optional

# ------------------------------------------------------------------
# Qt binding — PySide6 → PyQt6 → PyQt5 fallback
# ------------------------------------------------------------------
QT_ENGINE = None          # 'pyside6' | 'pyqt6' | 'pyqt5'

try:
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtCore import Qt, QTimer, QPoint, QRect
    from PySide6.QtGui import QFont, QColor, QPainter, QPalette, QPen, QBrush
    QT_ENGINE = "pyside6"
except ImportError:
    try:
        from PyQt6.QtWidgets import QApplication, QWidget
        from PyQt6.QtCore import Qt, QTimer, QPoint, QRect
        from PyQt6.QtGui import QFont, QColor, QPainter, QPalette, QPen, QBrush
        QT_ENGINE = "pyqt6"
    except ImportError:
        try:
            from PyQt5.QtWidgets import QApplication, QWidget
            from PyQt5.QtCore import Qt, QTimer, QPoint, QRect
            from PyQt5.QtGui import QFont, QColor, QPainter, QPalette, QPen, QBrush
            QT_ENGINE = "pyqt5"
        except ImportError:
            print("[overlay] Нужен PySide6 / PyQt6 / PyQt5")
            print("         pip install PyQt5   (или PySide6)")
            raise SystemExit(1)

import config as cfg

# ==================================================================
# Windows helpers — WS_EX_TOPMOST + click-through (WM_LBUTTONDOWN)
# ==================================================================
_GWL_EXSTYLE = -20
_SWS_SHOWNAME = 5  # SetWindowPos flag: force repaint


def _win_set_click_through(widget: QWidget):
    """Set WS_EX_TRANSPARENT on the window so mouse events pass through."""
    try:
        hwnd = widget.winId()

        # PyQt6 packs the HWND differently; PySide6 and PyQt5 are ints.
        if QT_ENGINE == "pyqt6":
            try:
                from PyQt6.QtCore import QWindow
            except ImportError:
                pass
            # For PyQt6 winId returns an int directly in recent versions
            # but may need casting depending on binding version.

        style = ctypes.windll.user32.GetWindowLongW(hwnd, _GWL_EXSTYLE)
        # WS_EX_TRANSPARENT  = 0x00000020
        # WS_EX_LAYERED     = 0x00080000   (needed for per-pixel translucency + click-through combo)
        style |= 0x00000020 | 0x00080000
        ctypes.windll.user32.SetWindowLongW(hwnd, _GWL_EXSTYLE, style)
        # Force the system to apply the new extended style
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            0x0002 | 0x0004 | 0x0010,   # SWP_NOSIZE | SWP_NOMOVE | SWP_FRAMECHANGED
        )
    except Exception:
        pass  # Non-Windows or unavailable — Qt flags handle the rest


def _win_set_topmost(widget: QWidget):
    """Force HWND_TOPMOST via WinAPI (belt-and-suspenders with Qt.WindowStaysOnTopHint)."""
    try:
        hwnd = widget.winId()
        HWND_TOPMOST = -1
        ctypes.windll.user32.SetWindowPos(
            hwnd, HWND_TOPMOST, 0, 0, 0, 0,
            0x0001 | 0x0002 | 0x0040,   # SWP_NOACTIVATE | SWP_NOSIZE | SWP_NOSENDCHANGING
        )
    except Exception:
        pass


# ==================================================================
# OverlayWidget — the actual transparent window
# ==================================================================
class OverlayWidget(QWidget):
    """
    Прозрачное TopMost + ClickThrough окно.

    Отображает «Слухи: X» с цветной рамкой, где цвет зависит от состояния
    сессии (idle / active / stopped).
    """

    # --- размеры и отступы -----------------------------------------
    WIDTH = 180
    HEIGHT = 44
    PADDING = 6       # внутренний отступ рисования
    BORDER_R = 8      # радиус скруглённой рамки

    # --- state → цвет mapping (переопределяется через set_count) ----
    _COLORS = {
        "idle":    cfg.Overlay.COLOR_IDLE,    # циан
        "active":  cfg.Overlay.COLOR_ACTIVE,  # зелёный
        "stopped": cfg.Overlay.COLOR_STOP,    # оранжевый
    }

    def __init__(self):
        super().__init__()

        o = cfg.Overlay

        # ------- window flags ---------------------------------------
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint   # без заголовка и рамки
            | Qt.WindowType.WindowStaysOnTopHint  # всегда сверху
            | Qt.WindowType.Tool                  # не попадает в taskbar
        )

        # ClickThrough: игнорируем mouse/touch события на уровне Qt
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        # Прозрачный фон (пиксельный alpha через paintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ------- geometry -------------------------------------------
        self.resize(self.WIDTH, self.HEIGHT)
        self.move(o.COUNTER_X, o.COUNTER_Y)

        # ------- state ------------------------------------------------
        self._count = 0
        self._state = "idle"   # idle | active | stopped

        # ------- WinAPI extras (no-op on Linux in dev / works on Win) -
        _win_set_click_through(self)
        _win_set_topmost(self)

    # ---- public API ------------------------------------------------
    def set_count(self, n: int, state: str = "idle"):
        """
        Обновить счётчик и состояние.

        Parameters
        ----------
        n : int
            Текущее количество слухов.
        state : str
            ``"idle"``  — ждём (циан)
            ``"active"`` — сессия запущена (зелёный)
            ``"stopped"`` — остановлена (оранжевый)
        """
        self._count = max(n, 0)
        self._state = state if state in self._COLORS else "idle"
        self.update()  # repaint

    def show(self):
        self.setVisible(True)

    def hide(self):
        self.setVisible(False)

    # ---- painting --------------------------------------------------
    def paintEvent(self, event):  # noqa: ARG002
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        color_rgb = self._COLORS.get(self._state, self._COLORS["idle"])

        # --- semi-transparent background ---
        bg = QColor(10, 10, 20, 170)   # тёмный полупрозрачный фон
        p.setBrush(QBrush(bg))
        border_pen = QPen(QColor(*color_rgb), 2)
        p.setPen(border_pen)
        p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), self.BORDER_R, self.BORDER_R)

        # --- text: "Слухи: X" ---
        o = cfg.Overlay
        font = QFont("Arial", o.COUNTER_FONTSIZE, QFont.Weight.Bold)
        p.setFont(font)
        p.setPen(QColor(*color_rgb))

        label = f"Слухи: {self._count}"
        fm = p.fontMetrics()
        # centred horizontally + vertically
        tw = fm.horizontalAdvance(label)
        th = fm.height()
        x = (self.WIDTH - tw) // 2
        y = (self.HEIGHT + th) // 2 + 2
        p.drawText(x, y, label)

        p.end()


# ==================================================================
# OverlayManager — singleton: manages the QApplication lifecycle
# ==================================================================
class OverlayManager:
    """
    Синглтон-менеджер оверлея.

    Управляет жизненным циклом QApplication (создаёт один раз,
    обрабатывает events из основного потока).
    """

    _instance: Optional["OverlayManager"] = None

    # -----------------------------------------------------------
    @classmethod
    def get_instance(cls) -> "OverlayManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -----------------------------------------------------------
    def __init__(self):
        self._app: Optional[QApplication] = None
        self._widget: Optional[OverlayWidget] = None
        self._ready = False

    # ---- init --------------------------------------------------
    def initialize(self):
        """Создать QApplication и виджет оверлея."""
        if self._ready:
            return

        try:
            self._app = QApplication.instance()
            if self._app is None:
                self._app = QApplication(sys.argv)
        except Exception as exc:
            print(f"[overlay] Не удалось создать QApplication: {exc}")
            return

        self._widget = OverlayWidget()
        self._ready = True
        self.hide()   # начинаем скрытым

    # ---- public ------------------------------------------------
    def set_count(self, n: int, state: str = "idle"):
        """Передаёт счётчик и состояние в виджет."""
        if self._widget:
            self._widget.set_count(n, state)

    def show(self):
        """Показать оверлей поверх игры."""
        if self._widget:
            self._widget.show()
            _win_set_topmost(self._widget)

    def hide(self):
        """Скрыть оверлей."""
        if self._widget:
            self._widget.hide()

    def process_events(self):
        """
        Обрабатывать Qt event-loop из основного (non-GUI) потока.

        Вызывать периодически (например, раз в секунду) чтобы
        окно оставалось отзывчивым.
        """
        if self._app:
            self._app.processEvents()

    def set_widget(self, widget: QWidget):
        """Вручную задать виджет для менеджера оверлея."""
        self._widget = widget


# =========================================================================
# Module-level convenience — import and use directly without manager pattern
# =========================================================================
_default_manager = OverlayManager()


def init():
    """Инициализировать оверлей (вызвать один раз при старте)."""
    _default_manager.initialize()


def set_count(n: int, state: str = "idle"):
    """Обновить счётчик «Слухи: n»."""
    _default_manager.set_count(n, state)


def show():
    """Показать оверлей."""
    _default_manager.show()


def hide():
    """Скрыть оверлей."""
    _default_manager.hide()


def process_events():
    """Прокачать Qt events из главного потока."""
    _default_manager.process_events()


# =========================================================================
# Standalone test — run `python utils/overlay.py` for a quick visual check
# =========================================================================
if __name__ == "__main__":
    import time

    init()

    states = ["idle", "active", "stopped"]
    show()
    for i in range(1, 20):
        set_count(i, state=states[i % 3])
        process_events()
        time.sleep(0.8)

    hide()
    sys.exit(0)
