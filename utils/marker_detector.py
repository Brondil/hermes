"""
Marker Detector - Автоматический поиск цветных прямоугольников на экране
Ня~ Находит красный, жёлтый и синий маркеры (=^･ω･^)

Маркеры (из скриншота-схемы):
- 🔴 Красный = RUMORS_REGION (где появляются руморы)
- 🟡 Жёлтый = OVERLAY_POSITION (где рисовать счётчик)
- 🔵 Синий/Голубой = TRIGGER_REGION (зона наведения мыши)
"""

import cv2
import numpy as np
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger("RumorTracker")


class MarkerDetector:
    """
    Автоматически ищет цветные прямоугольники-маркеры на экране, ня~!
    
    Каждая итерация трекинга:
    1. Захват экрана -> скриншот
    2. Поиск по цвету -> найти все 3 маркера
    3. Вернуть bounding-box каждого маркера
    """
    
    # Цветовые диапазоны в HSV для OpenCV
    # Красный (RUMORS_REGION) - два диапазона из-за обёртки hue
    RED_LOW1 = np.array([0, 150, 50])
    RED_HIGH1 = np.array([15, 255, 255])
    
    # Жёлтый (OVERLAY_POSITION)
    YELLOW_LOW = np.array([20, 150, 150])
    YELLOW_HIGH = np.array([35, 255, 255])
    
    # Синий/Голубой (TRIGGER_REGION)  
    BLUE_LOW = np.array([95, 150, 50])
    BLUE_HIGH = np.array([130, 255, 255])
    
    # Минимальный размер маркера в пикселях (чтобы не ловить шум)
    MIN_MARKER_AREA = 1000  # px²
    
    def __init__(self, debug_screenshots: bool = False):
        self.debug = debug_screenshots
        
    def find_all_markers(self, screen_img: np.ndarray) -> Dict[str, Optional[Tuple[int, int, int, int]]]:
        """
        Найти все 3 маркера на изображении экрана, ня~!
        
        Args:
            screen_img: BGR изображение от cv2 (скриншот экрана)
            
        Returns:
            Dict с координатами маркеров:
                'rumors_region': (x, y, w, h) красного маркера
                'overlay_position': (x, y, w, h) жёлтого маркера
                'trigger_region': (x, y, w, h) синего маркера
        """
        result = {
            'rumors_region': None,
            'overlay_position': None,
            'trigger_region': None,
        }
        
        # Конвертировать BGR -> HSV
        hsv = cv2.cvtColor(screen_img, cv2.COLOR_BGR2HSV)
        
        # Красный маркер (RUMORS_REGION) — два диапазона
        mask1 = cv2.inRange(hsv, self.RED_LOW1, self.RED_HIGH1)
        result['rumors_region'] = self._find_largest_rect(mask1, 'red')
        
        # Жёлтый маркер (OVERLAY_POSITION)
        mask_yel = cv2.inRange(hsv, self.YELLOW_LOW, self.YELLOW_HIGH)
        result['overlay_position'] = self._find_largest_rect(mask_yel, 'yellow')
        
        # Синий маркер (TRIGGER_REGION)
        mask_blue = cv2.inRange(hsv, self.BLUE_LOW, self.BLUE_HIGH)
        result['trigger_region'] = self._find_largest_rect(mask_blue, 'blue')
        
        return result
    
    def _find_largest_rect(self, mask: np.ndarray, color_name: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Найти наибольший прямоугольник в маске, ня~!
        
        Args:
            mask: Binarnaя маска от cv2.inRange
            color_name: имя цвета для логов
            
        Returns:
            (x, y, w, h) или None если маркер не найден
        """
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            logger.debug(f"Маркер {color_name}: контуры не найдены")
            return None
        
        # Фильтровать по минимальной площади (игнорировать шум)
        valid = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= self.MIN_MARKER_AREA:
                valid.append((cnt, area))
        
        if not valid:
            logger.debug(f"Маркер {color_name}: контуры слишком мелкие (мин. {self.MIN_MARKER_AREA}px²)")
            return None
        
        # Взять наибольший по площади
        best_cnt, best_area = max(valid, key=lambda x: x[1])
        x, y, w, h = cv2.boundingRect(best_cnt)
        
        logger.info(f"Найден маркер {color_name}: x={x} y={y} w={w} h={h} area={best_area}")
        return (x, y, w, h)
    
    def take_screenshot(self) -> np.ndarray:
        """Сделать скриншот экрана и вернуть BGR-изображение"""
        import pyautogui
        screenshot = pyautogui.screenshot()
        # pyautogui даёт RGB PIL -> numpy -> BGR для OpenCV
        img_rgb = np.array(screenshot)
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    def scan_and_update_config(self, screen_img: np.ndarray):
        """
        Сканировать экран и вернуть обновлённый config с найденными координатами
        """
        markers = self.find_all_markers(screen_img)
        
        found = 0
        total = 3
        
        if markers['rumors_region']:
            x, y, w, h = markers['rumors_region']
            print(f"  🔴 RUMORS_REGION: x={x}, y={y}, w={w}, h={h}")
            found += 1
        else:
            print("  🔴 RUMORS_REGION: не найден!")
            
        if markers['overlay_position']:
            x, y, w, h = markers['overlay_position']
            print(f"  🟡 OVERLAY_POSITION: x={x}, y={y}, w={w}, h={h}")
            found += 1
        else:
            print("  🟡 OVERLAY_POSITION: не найден!")
            
        if markers['trigger_region']:
            x, y, w, h = markers['trigger_region']
            print(f"  🔵 TRIGGER_REGION: x={x}, y={y}, w={w}, h={h}")
            found += 1
        else:
            print("  🔵 TRIGGER_REGION: не найден!")
        
        if found < total:
            logger.warning(f"Найдено только {found}/{total} маркеров из {total}")
        
        return markers
