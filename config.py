"""
Path of Exile 2 — Rumor Counter (PoE2 Rumor Tracker) Configuration
Ня~ Все параметры в одном месте (=^･ω･^)
По ТЗ: сессионный оверлей, F8 toggle, frame hash, fuzzy matching, PoE2 focus check
"""

import os

# ============================================================
# Пути
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "rumor_config.json")  # сохранение ROI

# ============================================================
# Игра — проверка фокуса (по имени процесса)
# ============================================================
GAME_PROCESS_NAME = "PathOfExile2.exe"

# ============================================================
# ROI — область экрана где появляются слухи
# Сохраняется в процентах (0.0-1.0), чтобы не съезжало при смене разрешения
# По умолчанию: правый верхний угол ~20%x20% для PoE2 UI панели
# ============================================================
class ROI:
    # Координаты левого верхнего угла и правого нижнего (в процентах экрана)
    X1 = 0.78  # слева
    Y1 = 0.05  # сверху
    X2 = 0.97  # справа
    Y2 = 0.35  # снизу

# ============================================================
# Сканер — цикл мониторинга
# ============================================================
class Scanner:
    # Задержка между сканами в режиме сессии (сек.)
    SCAN_INTERVAL = 1.0
    # Порог изменения хеша кадра чтобы запустить OCR
    # Чем выше — тем меньше ложных срабатываний, чем ниже — быстрее реагирует
    FRAME_HASH_THRESHOLD = 50  # Hamming distance

# ============================================================
# OCR + Fuzzy Matching (ТЗ п.5: критические суперфичи)
# ============================================================
class OCRSettings:
    # Fuzzy matching threshold: при каком % совпадения строка считается дубликатом
    # ТЗ: 90% совпадения = дубликат => не увеличивать счётчик
    FUZZY_THRESHOLD = 0.90
    
    # Максимальная длина строки (игнорировать очень длинные — мусор)
    MAX_LINE_LENGTH = 200
    # Минимальная длина строки (слишком короткие — мусорные символы)
    MIN_LINE_LENGTH = 3

# ============================================================
# Оверлей — прозрачный счётчик "Слухи: X" поверх игры
# Точка, размер и цвет. ТЗ п.3.1: TopMost + ClickThrough
# ============================================================
class Overlay:
    COUNTER_X     = 10
    COUNTER_Y     = 10
    COUNTER_FONTSIZE = 18
    
    # Цвета счётчика 
    COLOR_IDLE   = (0, 255, 255)   # Циан — ждём
    COLOR_ACTIVE = (0, 255, 0)     # Зелёный — сессия активна
    COLOR_STOP   = (255, 165, 0)   # Оранжевый — сессия остановлена

# ============================================================
# Хоткей
# ТЗ п.2: F8 toggle start/stop сессии
# ============================================================
class Hotkeys:
    TOGGLE_KEY = "f8"

# ============================================================
# Прочее
# ============================================================
class General:
    DEBUG_MODE = True
    LOG_FILE = "rumor_counter.log"


# ============================================================
# Runtime auto-detected values (set by scan_screen_markers / auto_detector)
# These override fallback values once the program runs.
# ============================================================

# Fallback for get_rumors_region() so main.py doesn't crash before auto-detect runs.
_FALLBACK_RUMORS_REGION = {
    "x": None,
    "y": None,
    "w": int(1920 * 0.19),   # 19% of width (X2-X1=0.97-0.78)
    "h": int(1080 * 0.30),   # 30% of height (Y2-Y1=0.35-0.05)
}

ACTIVE_RUMORS_REGION = None      # {x, y, w, h} — auto-detected table of rumors
ACTIVE_OVERLAY_POSITION = None   # (x, y) overlay counter position
ACTIVE_TRIGGER_REGION = None     # (x, y, w, h) hover zone for F9 trigger
ACTIVE_VORANA_POSITION = None    # (x, y) auto-detected Vorana's Saga click target


def get_rumors_region() -> dict:
    """Return active or fallback RUMORS_REGION."""
    if ACTIVE_RUMORS_REGION and all(v is not None for v in [ACTIVE_RUMORS_REGION.get('x'), ACTIVE_RUMORS_REGION.get('y')]):
        return ACTIVE_RUMORS_REGION
    # Build region from ROI percentages.
    roi = getattr(__import__('config', fromlist=['ROI']), 'ROI', None)
    
    # Default assumed resolution (will be overridden by auto-detected screen size in production).
    w, h = 1920, 1080
    return {
        "x": int(w * roi.X1) if roi else _FALLBACK_RUMORS_REGION['x'] or 1500,
        "y": int(h * roi.Y1) if roi else _FALLBACK_RUMORS_REGION['y'] or 54,
        "w": int(w * (roi.X2 - roi.X1)) if roi else _FALLBACK_RUMORS_REGION['w'] or 365,
        "h": int(h * (roi.Y2 - roi.Y1)) if roi else _FALLBACK_RUMORS_REGION['h'] or 324,
    }


def get_overlay_position() -> tuple:
    """Return active or fallback OVERLAY_POSITION."""
    if ACTIVE_OVERLAY_POSITION:
        return ACTIVE_OVERLAY_POSITION
    return (10, 10)  # default top-left corner of overlay window

