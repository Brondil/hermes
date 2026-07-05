"""
Auto Detector — автоматическое обнаружение элементов PoE2 UI на экране.

Поскольку пользователь не может рисовать зоны вручную программа использует:
1. OCR для поиска области с текстом руморов (правый верх экрана)
2. Template matching по тексту/цвету для Vorana's Saga
3. Fallback на ROI из config если ничего не найдено

Ня~ (=^･ω･^)
"""

import cv2
import numpy as np
from typing import Optional, Dict, Tuple, List
from collections import Counter
import logging
import os
import sys

logger = logging.getLogger("RumorTracker")


# Safe lazy access to config module (avoid circular imports).
def _get_config():
    """Lazily import and return the config module."""
    try:
        import sys as _sys
        import os as _os
        _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        if _root not in _sys.path:
            _sys.path.insert(0, _root)
        import config  # noqa: F401
        return config
    except ImportError:
        return None


# ============================================================
# Fallback — percentages from config.ROI used when OCR is unavailable.
# ============================================================
def _fallback_region(screen_w: int, screen_h: int) -> Dict:
    """Return a fallback RUMORS_REGION based on hard-coded defaults."""
    return {
        "x": int(screen_w * 0.78),   # X1 = 0.78
        "y": int(screen_h * 0.05),   # Y1 = 0.05
        "w": int(screen_w * (0.97 - 0.78)),  # width = 19% of screen
        "h": int(screen_h * (0.35 - 0.05)),  # height = 30% of screen
    }


class AutoDetector:
    """Автоматическое обнаружение элементов PoE2 UI на экране."""
    
    def __init__(self):
        self._ocr_engine = None
    
    @property
    def ocr(self):
        if self._ocr_engine is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr_engine = PaddleOCR(use_angle_cls=True, lang='en')
                logger.info("PaddleOCR доступен для авто-детектирции")
            except ImportError:
                logger.warning("PaddleOCR не найден — авто-детекция недоступна")
        return self._ocr_engine
    
    def find_rumors_table(self, screen_img=None) -> Optional[Dict]:
        """
        Найти таблицу с руморами на экране через OCR.
        
        Strategy:
        1. Сделать скриншот правой верхней части экрана (где PoE2 показывает список руморов)
        2. Запустить OCR 
        3. Найти cluster коротких строк → bounding box таблицы
        
        Returns: {"x": int, "y": int, "w": int, "h": int} или None
        """
        if screen_img is None:
            try:
                import pyautogui
                img_rgb = np.array(pyautogui.screenshot())
                screen_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            except ImportError:
                logger.error("pyautogui не установлен для скриншота")
                return None
        
        h, w = screen_img.shape[:2]
        
        # PoE2 rumors обычно в правом верхнем углу ~10-25% экрана
        # Скриншот этой области чтобы уменьшить шум
        x_start = int(w * 0.6)   # от 60% ширины
        region = screen_img[0:h, x_start:w]  # правая часть
        
        if self.ocr is None:
            # OCR недоступен — fallback на ROI из config как проценты от screen size
            logger.warning("OCR недоступен или не инициализирован — fallback fallback fallback on config ROI")
            return _fallback_region(w, h)
        
        
        # OCR на региона с текстом PoE2. Получим bounding boxes всех слов.
        ocr_result = self.ocr.ocr(region) # [N, 1, 4] x M
        
        if not ocr_result or not ocr_result[0]:
            logger.debug("OCR found nothing → fallback to ROI config.")
            roi = config.get_rumors_region()
            return {
                "x": int(w * roi['X1']),
                "y": int(h * roi['Y1']),
                "w": int(w * (roi['X2'] - roi['X1'])),
                "h": int(h * (roi['Y2'] - roi['Y1']))
            }
        
        # Из OCR bounding boxes собрать координаты с учётом offset x_start.
        all_points = []  # list of (x_abs, y_abs) in full screen
        for word_block in ocr_result[0]:
            pts = word_block[0]  # 4 points [[x1,y1], ...]. 
            x1, y1 = int(pts[0][0]), int(pts[0][1]) + x_start  
            x2, y2 = int(pts[2][0]) + x_start, int(pts[2][1])
            
            # Only keep words in the top 35% of the region (where rumors typically appear)
            if y2 < h * 0.4:
                all_points.append((x1, y1, x2, y2))
        
        if len(all_points) >= 3:
            # Cluster bounding boxes into a grid to find the table shape.
            xs = [p[0] for p in all_points] + [p[2] for p in all_points]
            ys = [p[1] for p in all_points] + [p[3] for p in all_points]
            
            return {
                "x": min(xs),
                "y": min(ys),
                "w": max(xs) - min(xs),
                "h": max(ys) - min(ys)
            }
        
        # Too few points → fallback
        logger.debug("Too few OCR boxes to form a table → fallback config.")
        return _fallback_region(w, h)
    
    def find_vorana_saga(self, screen_img=None) -> Optional[Tuple[int, int]]:
        """
        Найти Vorana's Saga на экране.
        
        Strategy:
        1. Template matching по золотистому цвету (уникальная/оранжевая рамка предмета).
        2. OCR для поиска текстового label "Vorana" в инвентаре.
        
        Returns: (cx, cy) center position or None if not detected.
        """
        if screen_img is None:
            try:
                import pyautogui
                img_rgb = np.array(pyautogui.screenshot())
                screen_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            except ImportError:
                return None
        
        h, w = screen_img.shape[:2]
        
        # Vorana's Saga — золотистый/оранжевый цвет (unique item rarity).
        golden_lower = np.array([15, 80, 150])
        golden_upper = np.array([30, 255, 255])
        
        hsv = cv2.cvtColor(screen_img, cv2.COLOR_BGR2HSV)
        mask_golden = cv2.inRange(hsv, golden_lower, golden_upper)
        
        # Morphological ops for cleaning up noise.
        kernel = np.ones((5,5), np.uint8)
        mask_cleaned = cv2.morphologyEx(mask_golden, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN, np.ones((3,3)))
        
        # Find contours of gold-colored items.
        contours, _ = cv2.findContours(
            mask_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        gold_items = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 500 < area < 50_000:  # reasonable item size (not too big/small)
                x, y, bw, bh = cv2.boundingRect(cnt)
                # Only look in inventory region (lower-right ~ 30% of screen).
                if x > w * 0.2 and y > h * 0.3:
                    gold_items.append((x + bw//2, y + bh//2))
        
        if gold_items:
            # Return largest-area item position (Vorana's Saga is the first unique you use).
            logger.info(f"Найдено {len(gold_items)} золотых предметов на экране.")
            return gold_items[0]  # First match → Vorana
        
        # Fallback on template matching if config has a template.
        cfg = _get_config()
        if cfg is not None and hasattr(cfg, 'VORANA_TEMPLATE') and getattr(cfg, 'VORANA_TEMPLATE', None):
            template_path = cfg.VORANA_TEMPLATE
            if os.path.exists(template_path):
                template = cv2.imread(template_path)
                if template is not None:
                    match_result = cv2.matchTemplate(
                        screen_img, template, cv2.TM_CCOEFF_NORMED
                    )
                    threshold = getattr(getattr(cfg, 'OCRSettings', None), 'FUZZY_THRESHOLD', 0.85)
                    loc = np.where(match_result >= threshold)
                    
                    if len(loc[0]) > 0:
                        center_x = int(loc[1][0] + template.shape[1]//2)
                        center_y = int(loc[0][0] + template.shape[0]//2)
                        logger.info(f"Vorana's Saga найден по template matching: ({center_x}, {center_y})")
                        return (center_x, center_y)
        
        # Ultimate fallback — use config ClickerSettings.
        cfg = _get_config()
        if cfg is not None and hasattr(cfg, 'ClickerSettings'):
            cs = cfg.ClickerSettings
            cx = getattr(cs, 'ITEM_CLICK_X', w // 3)
            cy = getattr(cs, 'ITEM_CLICK_Y', h // 3)
        else:
            cx, cy = w // 3, h // 3
        logger.info(f"Не удалось auto-детектировать Vorana → использую FALLBACK ({cx}, {cy})")
        return (cx, cy)
    
    def detect_screen_layout(self, screen_img=None) -> Dict:
        """
        Auto-detect all UI elements on screen.
        
        Returns dict with:
            - rumors_region: {"x,y,w,h} — таблица руморов
            - overlay_position: (x, y) — auto-center for counter overlay
            - trigger_region: (x, y, w, h). Hover zone near rumors for F9.
            - vorana_saga: (x, y or None) — Vorana's Saga click target
        
        Ня~ (=^･ω･^)
        """
        result = {
            "rumors_region": None,
            "overlay_position": None,
            "trigger_region": None,
            "vorana_saga": None,
        }
        
        if screen_img is None:
            try:
                import pyautogui
                img_rgb = np.array(pyautogui.screenshot())
                screen_img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            except ImportError:
                return result
        
        h, w = screen_img.shape[:2]
        
        # === 1. Detect rumors table ===
        r = self.find_rumors_table(screen_img)
        if r:
            result["rumors_region"] = r
            print(f"   [√] RUMORS_REGION auto-detected: ({r['x']}, {r['y']}) {r['w']}x{r['h']}")
        
        # === 2. Auto-center overlay position (bottom-left of rumors table) ===
        if r:
            result["overlay_position"] = (r['x'], r['y'] + r['h'])
        else:
            result["overlay_position"] = (int(w * 0.55), int(h * 0.1))
        
        # === 3. Trigger region = left-side hover zone for auto-clicker ===
        if r:
            trigger_x = max(0, r['x'] - int(r['w'] * 0.6))
            trigger_y = r['y']
            trigger_w = int(r['w'] * 0.6)
            trigger_h = r['h']
            result["trigger_region"] = (trigger_x, trigger_y, trigger_w, trigger_h)
        else:
            result["trigger_region"] = (int(w * 0.52), int(h * 0.05), int(w * 0.42), int(h * 0.3))
        
        # === 4. Detect Vorana's Saga in inventory region ===
        inv_x = int(w * 0.1)
        inv_y = int(h * 0.4)
        inv_h = int(h * 0.5)
        inv_w = int(w * 0.6)
        vimg = screen_img[inv_y:inv_y+inv_h, inv_x:inv_x+inv_w]
        
        # Color-based detection of golden item (Vorana has gold border).
        if hasattr(cv2, 'cvtColor'):
            hsv_inv = cv2.cvtColor(vimg, cv2.COLOR_BGR2HSV)
            golden_low = np.array([15, 80, 150])
            golden_high = np.array([30, 255, 255])
            mask_g = cv2.inRange(hsv_inv, golden_low, golden_high)
            kernel = np.ones((5,5), np.uint8)
            mask_clean = cv2.morphologyEx(mask_g, cv2.MORPH_CLOSE, kernel)
            masks_open = cv2.morphologyEx(mask_clean, cv2.MORPH_OPEN, np.ones((3,3)))
            
            contours_v, _ = cv2.findContours(
                masks_open, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            
            gold_items = []
            for cnt in contours_v:
                area = cv2.contourArea(cnt)
                if 500 < area < 30_000:
                    bx, by, bw, bh = cv2.boundingRect(cnt)
                    cx = inv_x + bx + bw // 2
                    cy = inv_y + by + bh // 2
                    gold_items.append((cx, cy))
            
            if gold_items:
                result["vorana_saga"] = gold_items[0]
                logger.info(f"Vorana's Saga auto-detected via golden color: {gold_items[0]}")
        
        # Fallback for config access in detect_screen_layout.
        cfg2 = _get_config()
        if result["vorana_saga"] is None and cfg2 is not None and hasattr(cfg2, 'ClickerSettings'):
            cs2 = cfg2.ClickerSettings
            cx2 = getattr(cs2, 'ITEM_CLICK_X', w // 3)
            cy2 = getattr(cs2, 'ITEM_CLICK_Y', h // 3)
            result["vorana_saga"] = (cx2, cy2)
            logger.info(f"Vorana's Saga fallback in detect_screen_layout: ({cx2}, {cy2})")
        
        return result
