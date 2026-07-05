"""
Rumor Tracker - Core Logic Module
Ня~ Главный модуль трекинга уникальных руморов в Poe 2 (=^･ω･^)

Workflow:
1. Игрок наводит мышь на элемент -> ловится нажатие F9
2. Скриншот regions с rumors -> OCR распознаёт текст
3. Vorana's Saga кликается 5 раз с паузой 2 сек
4. После каждого клика -> новый скриншот + OCR -> новые уникальные rumors
5. Результат выводится в оверлей поверх игры
"""

import os
import time
import cv2
import numpy as np
from collections import OrderedDict
from typing import Set, List, Tuple
import logging

from utils.screen_capture import ScreenCapture
from utils.ocr import RumorReader
from utils.auto_clicker import AutoClicker
from utils.overlay import OverlayManager
import config


# Setup logging
_g = getattr(config, 'General', None) or {}
_logging_file = _g.get('LOG_FILE', 'rumor_counter.log') if isinstance(_g, dict) else (getattr(_g, 'LOG_FILE', 'rumor_counter.log') if _g else 'rumor_counter.log')
_logging_level = (_g.get('DEBUG_MODE', False) if isinstance(_g, dict) else (getattr(_g, 'DEBUG_MODE', False) if _g else False))
logging.basicConfig(
    filename=_logging_file,
    level=logging.DEBUG if _logging_level else logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("RumorTracker")


class RumorTracker:
    """
    Основной класс трекинга руморов, ня~! 
    
    Процесс работы:
    1. Ждём триггер (нажатие F9 или наведение мыши на элемент Image 1)
    2. Делаем скриншот regions с rumors -> baseline уникальных руморов
    3. Кликаем "Vorana's Saga" 5 раз, после каждого клика проверяем новые руморы
    4. Аккумулируем все уникальные руморы
    5. Выводим результат через оверлей
    """
    
    def __init__(self):
        self.screen = ScreenCapture()
        self.reader = RumorReader()
        self.clicker = AutoClicker()
        self.overlay = OverlayManager.get_instance()
        
        # Сетка всех уникальных руморов за текущую сессию
        self.all_unique_rumors: Set[str] = set()
        
        # Инициализация oверлея
        self.overlay.initialize()
        logger.info("RumorTracker инициализирован, ня!")
    
    def _capture_rumors_region(self) -> Tuple[np.ndarray, int, int]:
        """Сделать скриншот regions с rumors"""
        return self.screen.capture_region(config.get_rumors_region())
    
    def _extract_unique_rumors(self, region_img: np.ndarray) -> List[str]:
        """Извлечь уникальные руморы из изображения региона"""
        return self.reader.extract_rumors(region_img)
    
    def _get_new_rumors(self, current: List[str], previous: Set[str]) -> Set[str]:
        """Найти новые руморы которых не было в предыдущем скриншоте"""
        new = set(current) - previous
        return new
    
    def run_baseline_scan(self) -> Tuple[List[str], Set[str]]:
        """
        Этап 1: Базовый scan при первом наведении.
        
        Захватывает регион с rumors и распознаёт базовые руморы ДО любых кликов.
        
        Returns: (list всех руморов, set уникальных)
        """
        print("[i] Этап 1: Базовый scan руморов...")
        logger.info("Начало базового scanа руморов")
        
        # Короткая пауза чтобы окно полностью появилось
        time.sleep(0.5)
        
        region_img, x_off, y_off = self._capture_rumors_region()
        rumors = self._extract_unique_rumors(region_img)
        unique = set(rumors)
        
        logger.info(f"Найдено {len(unique)} уникального руморов: {unique}")
        print(f"[+] Базовые уникальные руморы: {len(unique)}")
        
        return rumors, unique
    
    def run_click_cycle(self, baseline_rumors: Set[str]) -> Tuple[Set[str], int]:
        """
        Этапы 3-5: Цикл кликов по "Vorana's Saga".
        
        Для каждого из 5 кликов:
        1. Ждём CLICK_DELAY секунд
        2. Делаем клик по предмету
        3. Ждём WAIT_AFTER_CLICK для обновления UI
        4. Скриншот + OCR -> новые руморы
        5. Обновляем оверлей
        
        Returns: (все уникальные руморы, число новых)
        """
        print("[i] Этап 3-5: Цикл кликов по Vorana's Saga...")
        logger.info("Начало цикла кликов")
        
        all_rumors = set(baseline_rumors)
        new_this_cycle = 0

        for i in range(config.ClickerSettings.MAX_CLICKS):
            click_num = i + 1
            
            # 1. Найти и кликнуть по Vorana's Saga (Image 3 -> 4)
            screen_img = self.screen.capture_screen()
            pos = self.clicker.find_item_on_screen(screen_img)
            
            if pos is None:
                if config.VORANA_TEMPLATE and os.path.exists(config.VORANA_TEMPLATE):
                    print(f"[!] Клик {click_num}: Не удалось найти Vorana's Saga!")
                    logger.warning(f"Клик {click_num}: Template not found on screen")
                else:
                    print(f"[i] Клик {click_num}: Шаблон не настроен, использую фиксированную позицию")
                    pos = (config.ClickerSettings.ITEM_CLICK_X, config.ClickerSettings.ITEM_CLICK_Y)
            
            self.clicker.click_at_position(pos[0], pos[1])
            
            print(f"[+] Клик {click_num}/{config.ClickerSettings.MAX_CLICKS}...")
            logger.info(f"Клик номер {click_num}")
            
            # 2. Ждем обновления UI
            time.sleep(config.ClickerSettings.WAIT_AFTER_CLICK)
            
            # 3. Скриншот региона rumors и распознавание
            region_img, _, _ = self._capture_rumors_region()
            rumors = self._extract_unique_rumors(region_img)
            
            # 4. Найти НОВЫЕ уникальные руморы
            newly_found = self._get_new_rumors(rumors, all_rumors)
            new_this_cycle += len(newly_found)
            
            # 5. Добавляем все найденные
            all_rumors.update(rumors)
            
            # 6. Обновить оверлей
            base = len(baseline_rumors)
            total = len(all_rumors)
            self.overlay.update_counter(base, new_this_cycle, total, click_num)
            
            print(f"[+] После клика {click_num}: +{len(newly_found)} новых уникальных "
                  f"| Всего: {total}")
            logger.debug(f"Новые руморы после клика {click_num}: {newly_found}")
            
            # 7. Интервал перед следующим кликом (если есть)
            if i < config.ClickerSettings.MAX_CLICKS - 1:
                time.sleep(config.ClickerSettings.CLICK_DELAY)
        
        logger.info(f"Цикл завершён. Всего уникальных руморов: {len(all_rumors)}")
        return all_rumors, new_this_cycle
    
    def run_full_track(self):
        """
        Полный workflow трекинга:
        
        Этап 1 (Image 1 -> Image 2): Наведение на элемент -> baseline scan
        Этап 3-5 (Image 3 -> 4): Цикл кликов + подсчет новых руморов  
        Этап финальный (Image 5): Вывод результата в оверлей
        
        Ня~ запускаем! 🐾
        """
        print("="*50)
        print("🐾 Poe 2 Rumor Tracker — запуск! 🐾")
        print("="*50)
        
        try:
            # === Этап 1-2: Baseline scan руморов ===
            all_rumors_list, baseline_unique = self.run_baseline_scan()
            
            # Запоминаем все руморы этой сессии
            self.all_unique_rumors.update(baseline_unique)
            
            # === Этапы 3-5: Цикл кликов по Vorana's Saga ===
            all_unique, new_count = self.run_click_cycle(baseline_unique)
            
            # Обновляем глобальный set
            self.all_unique_rumors.update(all_unique)
            
            # === Финальный вывод в oверлей ===
            final_total = len(self.all_unique_rumors)
            self.overlay.update_counter(
                base=len(baseline_unique),
                new=new_count,
                total=final_total,
                click_num=config.ClickerSettings.MAX_CLICKS
            )
            
            print("="*50)
            print(f"✅ Готово! Всего уникальных руморов: {final_total}")
            print(f"   Базовые: {len(baseline_unique)}")
            print(f"   Новые: +{new_count}")
            print("="*50)
            
            # Логируем список для отладки
            logger.info(f"ФИНАЛ: Всего уникальных руморов = {final_total}")
            logger.debug(f"Все руморы: {sorted(self.all_unique_rumors)}")
            
        except Exception as e:
            print(f"[!] ОШИБКА: {e}")
            logger.error(f"Критическая ошибка в run_full_track: {e}", exc_info=True)
        
        finally:
            # Обновляем Qt events
            self.overlay.process_events()
