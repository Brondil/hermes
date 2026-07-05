"""
Screen Capture & Template Matching Module
Ня~ Модуль захвата экрана и поиска шаблонов (=^･ω･^)
"""

import pyautogui
import numpy as np
import cv2
from typing import Tuple, Optional, List
import time
import config


class ScreenCapture:
    """Модуль для захвата экрана и поиска элементов, ня~"""
    
    def __init__(self):
        # Отключаю тайм-out pyautogui для безопасности
        pyautogui.FAILSAFE = True
        
    def capture_screen(self) -> np.ndarray:
        """Сделать скриншот всего экрана"""
        screenshot = pyautogui.screenshot()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    def capture_region(self, region: dict) -> Tuple[np.ndarray, int, int]:
        """
        Захватить регион экрана.
        Возвращает (image, x_offset, y_offset)
        """
        screenshot = pyautogui.screenshot()
        img = np.array(screenshot)
        
        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
        region_img = img[y:y+h, x:x+w]
        return region_img, x, y
    
    def find_template(self, screenshot: np.ndarray, template_path: str, 
                      threshold: float = None, region: dict = None) -> Optional[Tuple[int, int]]:
        """
        Найти шаблон на скриншоте.
        Возвращает (x, y) центра найденного элемента или None.
        """
        if threshold is None:
            threshold = config.OCRSettings.MATCH_THRESHOLD
            
        template = cv2.imread(template_path)
        if template is None:
            print(f"[!] Не удалось загрузить шаблон: {template_path}")
            return None
        
        # Если задан регион, обрезаем скриншот
        if region:
            x_off, y_off = region["x"], region["y"]
            h, w = region["h"], region["w"]
            search_area = screenshot[y_off:y_off+h, x_off:x_off+w]
        else:
            search_area = screenshot
        
        result = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            center_x = max_loc[0] + template.shape[1] // 2
            center_y = max_loc[1] + template.shape[0] // 2
            
            if region:
                center_x += region["x"]
                center_y += region["y"]
            
            return (center_x, center_y)
        
        return None
    
    def wait_for_template(self, template_path: str, timeout: float = 10.0, 
                          check_interval: float = 0.5, region: dict = None) -> bool:
        """
        Ждать появления шаблона на экране.
        Возвращает True если найден, False если таймаут.
        """
        start = time.time()
        while time.time() - start < timeout:
            screenshot = self.capture_screen()
            result = self.find_template(screenshot, template_path, region=region)
            if result is not None:
                return True
            time.sleep(check_interval)
        return False


# Инициализация глобального экземпляра
screen = ScreenCapture()
