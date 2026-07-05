"""
Auto Clicker Module - Vorana's Saga clicking logic
Ня~ Автоматические клики по предмету (=^･ω･^)
"""

import pyautogui
import time
import cv2
import numpy as np
from typing import Optional, Tuple
import config


class AutoClicker:
    """Автоматически кликает на Vorana's Saga в инвентаре, ня~"""
    
    def __init__(self):
        pyautogui.FAILSAFE = True  # Двигаем мышь в угол для экстренного stop
        self.click_count = 0
    
    def find_item_on_screen(self, screenshot: np.ndarray) -> Optional[Tuple[int, int]]:
        """
        Найти "Vorana's Saga" на скриншоте через template matching.
        Если шаблон не найден - используется фиксированная позиция.
        """
        # Try template matching first
        result = None
        if config.VORANA_TEMPLATE and cv2.imread(config.VORANA_TEMPLATE) is not None:
            template = cv2.imread(config.VORANA_TEMPLATE)
            
            # Search only in inventory region for speed
            region = config.INVENTORY_REGION
            x_off, y_off = region["x"], region["y"]
            h, w = region["h"], region["w"]
            search_area = screenshot[y_off:y_off+h, x_off:x_off+w]
            
            match_result = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
            max_val = match_result.max()
            
            if max_val >= config.OCRSettings.MATCH_THRESHOLD:
                loc = np.unravel_index(match_result.argmax(), match_result.shape)
                result = (loc[1] + x_off + template.shape[1]//2, 
                         loc[0] + y_off + template.shape[0]//2)
        
        return result
    
    def click_at_position(self, pos_x: int, pos_y: int):
        """Кликнуть в указанную позицию мыши"""
        pyautogui.click(pos_x, pos_y)
        time.sleep(0.1)  # Пауза после клика
    
    def run_cycle(self, screenshot_func=None) -> int:
        """
        Запустить цикл нажатий:
        - Найти Vorana's Saga 
        - Кликнуть MAX_CLICKS раз с интервалом CLICK_DELAY
        
        Returns кол-во успешных кликов
        """
        successful_clicks = 0
        
        # Пытаемся найти позицию предмета
        for i in range(config.ClickerSettings.MAX_CLICKS):
            # Получаем свежий скриншот
            if screenshot_func:
                screen_img = screenshot_func()
                pos = self.find_item_on_screen(screen_img)
            
            if pos:
                self.click_at_position(pos[0], pos[1])
                successful_clicks += 1
            else:
                print(f"[!] Клик {i+1}: Не удалось найти Vorana's Saga!")
                break
            
            # Интервал между кликами
            if i < config.ClickerSettings.MAX_CLICKS - 1:
                time.sleep(config.ClickerSettings.CLICK_DELAY)
        
        return successful_clicks


# Глобальный экземпляр
autoclicker = AutoClicker()
