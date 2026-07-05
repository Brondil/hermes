"""
OCR Module - Rumor Text Recognition
Ня~ Распознавание текста руморов (=^･ω･^)
Uses PaddleOCR as primary (more accurate for game text) with Tesseract fallback
"""

import cv2
import numpy as np
from typing import List, Set
import time
import re


class RumorReader:
    """Читает текст rumors из игры через OCR, ня~"""
    
    def __init__(self):
        self._paddle_ocr = None
        self._tesseract = None
        self._use_paddle = False
        
        # Pытаюсь загрузить PaddleOCR (более точный для игрового текста)
        try:
            from paddleocr import PaddleOCR
            self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            self._use_paddle = True
            print("[OK] PaddleOCR загружен!")
        except ImportError:
            print("[i] PaddleOCR не найден, будет использован Tesseract")
        
        # Fallback на Tesseract
        if not self._use_paddle:
            try:
                import pytesseract
                tesseract_exe = None
                try:
                    import config
                    tesseract_exe = config.OCRSettings.TESSERACT_CMD
                except:
                    pass
                if tesseract_exe:
                    pytesseract.pytesseract.tesseract_cmd = tesseract_exe
                self._tesseract = pytesseract
                print("[OK] Tesseract загружен!")
            except ImportError:
                print("[!] Ни PaddleOCR, ни Tesseract не найдены!")
                print("[i] Установите один из них:")
                print("    pip install paddleocr")
                print("    или pip install pytesseract + установить Tesseract OCR")
    
    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """Подготовка изображения для OCR"""
        # Конвертация в градации серого
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Убираем шум
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        
        # Бinarизation с adaptive threshold
        binary = cv2.adaptiveThreshold(
            denoised, 255, 
            cv2.THRESH_BINARY, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            blockSize=11, C=2
        )
        
        # Немного размыть для лучшего распознавания
        blurred = cv2.GaussianBlur(binary, (1, 1), 0)
        
        return blurred
    
    def extract_rumors(self, region_img: np.ndarray) -> List[str]:
        """
        Извлечь список rumors из региона экрана.
        
        Args:
            region_img: numpy array изображения региона с rumors
            
        Returns:
            List уникальных строк-руморов
        """
        preprocessed = self._preprocess(region_img)
        raw_lines = []
        
        if self._use_paddle and self._paddle_ocr:
            # PaddleOCR path
            result = self._paddle_ocr.ocr(preprocessed, cls=True)
            if result and result[0]:
                for line in result[0]:
                    box, (text, confidence) = line
                    if confidence > 0.6:
                        text = text.strip()
                        raw_lines.append(text)
        elif self._tesseract:
            # Tesseract path
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,;:\'!?-'
            text = self._tesseract.image_to_string(preprocessed, config=custom_config)
            raw_lines = [line.strip() for line in text.split('\n') if line.strip()]
        else:
            print("[OCR] Нет доступного OCR движка!")
            return []
        
        # Фильтруем результат - оставляем только строки похожие на rumors
        rumors = self._filter_rumors(raw_lines)
        return rumors
    
    def _filter_rumors(self, raw_lines: List[str]) -> List[str]:
        """
        Фильтрует распознанный текст - оставляет только rumors.
        
        Rumor'ы обычно содержат определенные ключевые слова или паттерны.
        Ня настроится под конкретный формат руморов в Poe 2~
        """
        # Паттерны которые НЕ являются rumors (игровой UI мусор)
        skip_patterns = [
            r'^Quality:',
            r'^Item Level:',
            r'^Socket',
            r'^Rare ',
            r'^Magic ',
            r'^Normal ',
            r'^Quantity:',
            r'^Physical Damage Reduction',
            r'^(Block|Evasion|Energy Shield)',
        ]
        
        # Паттерны которые МОГУТ быть rumors
        rumor_patterns = [
            r'[Rr]umor',
            r'[Ww]hisper',
            r'[Gg]ossip',
            r'[Rr]umour',
        ]
        
        filtered = []
        for line in raw_lines:
            # Пропускаем пустые и слишком короткие строки
            if len(line) < 3 or len(line) > 200:
                continue
            
            # Пропускаем UI-элементы
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line):
                    skip = True
                    break
            
            if not skip:
                # Проверяем похож ли на rumor (по ключевым словам)
                # Если ни один профиль не подошёл, всё равно сохраняем 
                # - потому что rumors могут быть любыми строками
                has_rumor_keyword = any(re.search(p, line) for p in rumor_patterns)
                
                if has_rumor_keyword:
                    filtered.append(line)
        
        return filtered
    
    def get_unique_count(self, rumors_list: List[str]) -> int:
        """Получить кол-во уникальных руморов"""
        unique = set(rumors_list)
        return len(unique)


# Глобальный экземпляр
rumor_reader = RumorReader()
