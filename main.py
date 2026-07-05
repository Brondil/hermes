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

from utils.tracker import RumorTracker
from utils.hotkey import HoverListener
from utils.overlay import OverlayManager, OverlayWidget
from utils.marker_detector import MarkerDetector
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
        help=f"X-координата региона руморов (default: {config.FALLBACK_RUMORS_REGION['x']})"
    )
    parser.add_argument(
        "--region-y", type=int, default=None,
        help=f"Y-координата региона руморов (default: {config.FALLBACK_RUMORS_REGION['y']})"
    )
    parser.add_argument(
        "--overlay-x", type=int, default=None,
        help=f"X позиция оверлея (default: {config.OverlaySettings.POSITION_X})"
    )
    parser.add_argument(
        "--overlay-y", type=int, default=None,
        help=f"Y позиция оверлея (default: {config.OverlaySettings.POSITION_Y})"
    )
    parser.add_argument(
        "--clicks", type=int, default=None,
        help=f"Количество кликов по Vorana's Saga (default: {config.ClickerSettings.MAX_CLICKS})"
    )
    parser.add_argument(
        "--delay", type=float, default=None,
        help=f"Задержка между кликами в секундах (default: {config.ClickerSettings.CLICK_DELAY})"
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
        config.FALLBACK_RUMORS_REGION["x"] = args.region_x
    if args.region_y is not None:
        config.FALLBACK_RUMORS_REGION["y"] = args.region_y
    if args.overlay_x is not None:
        config.OverlaySettings.POSITION_X = args.overlay_x
    if args.overlay_y is not None:
        config.OverlaySettings.POSITION_Y = args.overlay_y
    if args.clicks is not None:
        config.ClickerSettings.MAX_CLICKS = args.clicks
    if args.delay is not None:
        config.ClickerSettings.CLICK_DELAY = args.delay
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
    """Сканировать экран и найти цветные маркеры, ня~"""
    print("[🔍] Сканирование экрана на наличие цветных прямоугольников-маркеров...")
    print("   🔴 Красный  -> RUMORS_REGION")
    print("   🟡 Жёлтый  -> OVERLAY_POSITION")
    print("   🔵 Синий   -> TRIGGER_REGION")
    
    try:
        detector = MarkerDetector()
        screen_img = detector.take_screenshot()
        
        red_rects = detector.find_color_region(screen_img, detector.RED)
        yellow_rects = detector.find_color_region(screen_img, detector.YELLOW)
        blue_rects = detector.find_color_region(screen_img, detector.BLUE)
        
        found_any = False
        
        if red_rects:
            best = detector.best_fit_rect(red_rects)
            config.ACTIVE_RUMORS_REGION = {
                "x": best["x"], "y": best["y"],
                "w": best["width"], "h": best["height"]
            }
            print(f"   [✓] 🔴 RUMORS_REGION найден: ({best['x']}, {best['y']}) {best['width']}x{best['height']}")
            found_any = True
        
        if yellow_rects:
            centroid = detector.centroid_of_blobs(yellow_rects)
            config.ACTIVE_OVERLAY_POSITION = (centroid[0], centroid[1])
            print(f"   [✓] 🟡 OVERLAY_POSITION найден: ({centroid[0]}, {centroid[1]})")
            found_any = True
        
        if blue_rects:
            best = detector.best_fit_rect(blue_rects)
            config.ACTIVE_TRIGGER_REGION = (best["x"], best["y"], best["width"], best["height"])
            print(f"   [✓] 🔵 TRIGGER_REGION найден: ({best['x']}, {best['y']}) {best['width']}x{best['height']}")
            found_any = True
        
        if not found_any:
            print("   [!] Маркеры не найдены — используются fallback координаты из config.py")
            detector.save_debug_screenshot(screen_img, red_rects, yellow_rects, blue_rects)
        
    except Exception as e:
        print(f"   [!] Ошибка сканирования экрана: {e}")
        print("   [!] Используются fallback координаты")


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
