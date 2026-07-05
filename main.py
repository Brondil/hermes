"""
========================================
Poe 2 — Vorana's Saga Rumor Tracker
Ня~ Главная точка входа (=^･ω･^)

Запустить: python main.py

Автор: Neko-chan 🐾
Для: Fonkrac ❤️
========================================
"""

import sys
import os
import time
import argparse

# Добавляем директорию проекта в путь для импорта модулей
sys.path.insert(0, os.path.dirname(__file__))

from utils.screen_capture import ScreenCapture
from utils.ocr import RumorReader
from utils.auto_clicker import AutoClicker
from utils.overlay import OverlayManager, OverlayWidget
from utils.auto_detector import AutoDetector
from utils.tracker import RumorTracker
from utils.hotkey import HoverListener
# QApplication для оверлея
try:
    from PySide6.QtWidgets import QApplication
except ImportError:
    from PyQt6.QtWidgets import QApplication
import config


def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Poe 2 Vorana's Saga Rumor Tracker 🐾"
    )
    parser.add_argument(
        "--mode", choices=["hotkey", "hover"], default="hotkey",
        help="Режим запуска: хоткей F9 или hover над зоной (default: hotkey)"
    )
    parser.add_argument(
        "--hover-region", nargs=4, type=int, metavar=("X", "Y", "W", "H"),
        help="Координаты зоны ховера для режима hover (x y w h)"
    )
    parser.add_argument(
        "--region-x", type=int, default=None,
        help=f"X-координата региона руморов (default: {_FALLBACK_RUMORS_REGION['x'] or 1500})"
    )
    parser.add_argument(
        "--region-y", type=int, default=None,
        help=f"Y-координата региона руморов (default: {_FALLBACK_RUMORS_REGION.get('y', 54) or 54})"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Выполнить один цикл трекинга и завершить (без хоткея)"
    )
    parser.add_argument(
        "--threshold", type=float, default=None,
        help=f"Порог template matching 0-1 (default: {config.OCRSettings.MATCH_THRESHOLD})"
    )
    
    args = parser.parse_args()
    
    # Применить настройки из аргументов (перезаписывают fallback)
    if args.region_x is not None:
        _FALLBACK_RUMORS_REGION["x"] = args.region_x
    if args.region_y is not None:
        _FALLBACK_RUMORS_REGION["y"] = args.region_y
    if args.threshold is not None:
        config.OCRSettings.MATCH_THRESHOLD = args.threshold
    
    return args


def print_banner():
    """Баннер программы, ня~"""
    print()
    print("╔════════════════════════════════════════════════════╗")
    print("║   🐾  Poe 2 — Vorana's Saga Rumor Tracker  🐾     ║")
    print("║                                                  ║")
    print("║   Разработано: Neko-chan (=^･ω･^)                ║")
    print("║   Для: Fonkrac ❤️                                 ║")
    print("╚════════════════════════════════════════════════════╝")
    print()


def scan_screen_markers():
    """
    Автоматический поиск UI элементов PoE2 на экране.
    
    Вместо ручного рисования зон программа сама:
    1. OCR → ищет область с текстом руморов (правый верх)
    2. Цветовой анализ золотых предметов → находит Vorana's Saga
    3. Fallback на config ROI если ничего не найдено
    
    Ня~ (=^･ω･^)
    """
    print("[🔍] Автоматический поиск элементов PoE2 UI...")
    
    try:
        detector = AutoDetector()
        
        # detect_screen_layout() takes screenshot internally when screen_img=None
        layout = detector.detect_screen_layout(None)
        
        # Применяем найденные координаты.
        found_any = False
        
        rumors_r = layout.get('rumors_region')
        overlay_p = layout.get('overlay_position')
        trigger_r = layout.get('trigger_region')
        vorana_s = layout.get('vorana_saga')
        
        if rumors_r:
            config.ACTIVE_RUMORS_REGION = {
                "x": rumors_r['x'], "y": rumors_r['y'],
                "w": rumors_r['w'], "h": rumors_r['h']
            }
            print(f"   [√] RUMORS_REGION auto-detected: ({rumors_r['x']}, {rumors_r['y']}) {rumors_r['w']}x{rumors_r['h']}")
            found_any = True
        else:
            print("   [!] Таблица руморов не найдена OCR → fallback config.")
        
        if overlay_p:
            config.ACTIVE_OVERLAY_POSITION = overlay_p
            print(f"   [√] OVERLAY_POSITION auto-detected: ({overlay_p[0]}, {overlay_p[1]})")
            found_any = True
        else:
            config.ACTIVE_OVERLAY_POSITION = (config.Overlay.COUNTER_X, config.Overlay.COUNTER_Y)
        
        if trigger_r:
            config.ACTIVE_TRIGGER_REGION = trigger_r
            print(f"   [√] TRIGGER_REGION auto-detected: ({trigger_r[0]}, {trigger_r[1]}) {trigger_r[2]}x{trigger_r[3]}")
            found_any = True
        
        if vorana_s:
            config.ACTIVE_VORANA_POSITION = vorana_s
            print(f"   [√] Vorana's Saga auto-detected: ({vorana_s[0]}, {vorana_s[1]})")
            found_any = True
        
        if not found_any and hasattr(config, 'ROI'):
            _apply_config_fallback()
        
    except Exception as e:
        print(f"   [!] Ошибка авто-поиска UI элементов: {e}")
        print("   [!] Используются fallback координаты из config.py")
        _apply_config_fallback()


def _apply_config_fallback():
    """Применить fallback ROI из config при отсутствии auto-detected значений."""
    if hasattr(config, 'ROI'):
        roi = config.ROI
        w_full = 1920  # assumed default screen width
        h_full = 1080  # assumed default screen height
        
        # Apply percentages to absolute coordinates.
        config.ACTIVE_RUMORS_REGION = {
            "x": int(w_full * roi.X1),
            "y": int(h_full * roi.Y1),
            "w": int(w_full * (roi.X2 - roi.X1)),
            "h": int(h_full * (roi.Y2 - roi.Y1))
        }
        
        config.ACTIVE_OVERLAY_POSITION = (
            w_full // 2,
            h_full // 4
        )
        
        trigger_x = max(0, config.ACTIVE_RUMORS_REGION['x'] - int(config.ACTIVE_RUMORS_REGION['w'] * 0.6))
        trigger_y = config.ACTIVE_RUMORS_REGION['y']
        trigger_w = int(config.ACTIVE_RUMORS_REGION['w'] * 0.6)
        trigger_h = config.ACTIVE_RUMORS_REGION['h']
        config.ACTIVE_TRIGGER_REGION = (trigger_x, trigger_y, trigger_w, trigger_h)


def get_effective_trigger_region():
    """Вернуть регион для hover (из маркера или аргументов)"""
    if config.ACTIVE_TRIGGER_REGION:
        return config.ACTIVE_TRIGGER_REGION
    return None


def main():
    args = parse_args()
    print_banner()
    
    # Проверка зависимостей
    check_dependencies()
    
    # === Сканирование экрана на маркеры ===
    scan_screen_markers()
    
    # Показать какие координаты задействованы
    rumors = config.get_rumors_region()
    overlay_pos = config.get_overlay_position()
    trigger = config.ACTIVE_TRIGGER_REGION or "(не найден, будет F9)"
    print(f"\n[📐] Активные координаты:")
    print(f"     🔴 RUMORS_REGION:  ({rumors['x']}, {rumors['y']}) {rumors['w']}x{rumors['h']}")
    print(f"     🟡 OVERLAY_POS:    ({overlay_pos[0]}, {overlay_pos[1]})")
    print(f"     🔵 TRIGGER_REGION: {trigger}")
    
    # Инициализация оверлея с динамической позицией
    overlay_x, overlay_y = config.get_overlay_position()
    app = QApplication(sys.argv)
    overlay_mgr = OverlayManager()
    overlay_widget = OverlayWidget(pos_x=overlay_x, pos_y=overlay_y)
    overlay_mgr.set_widget(overlay_widget)
    
    # Инициализация трекера
    tracker = RumorTracker()
    tracker.overlay_manager = overlay_mgr
    
    if args.once:
        # Режим одного запуска — без хоткея, сразу треким и выходим
        print("[i] Режим: один запуск")
        tracker.run_full_track()
        return
    
    # Настройка триггера —优先 синие маркерные координаты
    effective_trigger_region = None
    if trigger == "(не найден, будет F9)":
        effective_trigger_region = None
    else:
        effective_trigger_region = tuple(trigger) if isinstance(trigger, tuple) else trigger
    if args.hover_region and args.mode == "hover":
        effective_trigger_region = tuple(args.hover_region)
    
    listener = HoverListener(
        trigger_region=effective_trigger_region,
        hover_duration=1.5,
        mode=args.mode
    )
    
    print(f"\n[i] Готово к работе!")
    if args.mode == "hotkey":
        print("[i] Нажми F9 чтобы запустить трекер руморов")
        print("[i] Кликни в угол экрана для экстренной остановки (pyautogui failsafe)")
    elif effective_trigger_region:
        r = effective_trigger_region
        print(f"[i] Наведи мышь на область ({r[0]}, {r[1]}) {r[2]}x{r[3]} чтобы запустить трекер")
    
    # Установить callback при нажатии триггера
    listener.set_callback(tracker.run_full_track)
    
    try:
        listener.start()  # Blocking — работает пока не завершится
    except KeyboardInterrupt:
        print("\n[👋] Завершение... Ня~")
        
        # Скрыть oверлей перед выходом
        overlay_mgr.hide()



def check_dependencies():
    """Проверить что все нужные пакеты установлены, ня~"""
    missing = []
    
    checks = [
        ("PyQt6 или PySide6", ["PyQt6.QtWidgets", "PySide6.QtWidgets"]),
    ]
    
    # Проверяю Qt-framework
    has_qt = False
    for mod in ["PyQt6.QtWidgets", "PySide6.QtWidgets"]:
        try:
            __import__(mod)
            print(f"[OK] {mod.split('.')[0]} найден")
            has_qt = True
            break
        except ImportError:
            pass
    
    if not has_qt:
        missing.append("PyQt6 или PySide6 (для оверлея)")
    
    # Проверяю OpenCV
    try:
        import cv2
        print(f"[OK] OpenCV найден (v{cv2.__version__})")
    except ImportError:
        missing.append("opencv-python (для template matching)")
    
    # Проверяю OCR движок
    has_ocr = False
    
    try:
        from paddleocr import PaddleOCR
        print("[OK] PaddleOCR найден — используется как основной")
        has_ocr = True
    except ImportError:
        pass
    
    if not has_ocr:
        try:
            import pytesseract
            print("[OK] PyTesseract найден — используется как fallback")
            has_ocr = True
        except ImportError:
            missing.append("pytesseract или paddleocr (для чтения текста руморов)")
    
    # Проверяю pyautogui
    try:
        import pyautogui
        print("[OK] PyAutoGUI найден")
    except ImportError:
        missing.append("pyautogui (для автоматических кликов)")
    
    # Проверяю pynput
    try:
        import pynput
        print("[OK] Pynput найден")
    except ImportError:
        missing.append("pynput (для захвата F9 / hover)")
    
    if missing:
        print("\n[!] НЕ ХВАТАЕТ зависимостей:")
        for pkg in missing:
            print(f"    - {pkg}")
        print("\nУстановить: pip install " + " ".join(missing))
        print("\nИли все сразу: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
