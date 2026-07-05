"""
Screen Capture Module - Screenshot capture for Poe 2
Ня~ Делает скриншоты экрана для OCR и поиска (=^･ω･^)
Uses mss for fast screen capture + pillow/pyautogui fallback
Returns: Tuple[np.ndarray, x_offset, y_offset]
"""

import cv2
import numpy as np
from typing import Tuple


class ScreenCapture:
    """Быстрый захват экрана с определённого монитора, ня~"""
    
    def __init__(self):
        self._screenshot_lib = None
    
    def _ensure_lib(self):
        """Подгрузить mss или pillow"""
        if self._screenshot_lib is not None:
            return
        
        # Try mss first (fastest)
        try:
            import mss
            self._screenshot_lib = mss.mss()
            self._lib_type = 'mss'
        except ImportError:
            pass
        
        # Fallback to Pillow
        if self._screenshot_lib is None:
            try:
                from PIL import ImageGrab
                self._screenshot_lib = ImageGrab
                self._lib_type = 'PIL'
            except ImportError:
                pass
        
        # Last resort: pyautogui
        if self._screenshot_lib is None:
            try:
                import pyautogui
                self._screenshot_lib = pyautogui
                self._lib_type = 'pyautogui'
            except ImportError:
                raise ImportError(
                    "Нужен mss, PIL (pillow) или pyautogui для скриншотов! Ня~ :("
                )
    
    def capture_screen(self) -> np.ndarray:
        """
        Скриншот всего экрана.
        Returns: BGR numpy array (для OpenCV)
        """
        self._ensure_lib()
        
        if self._lib_type == 'mss':
            s = self._screenshot_lib
            monitor = {"top": 0, "left": 0, "width": s.monitors[1]["width"], 
                      "height": s.monitors[1]["height"]}
            img = s.grab(monitor)
            return np.array(img)[:,:,:3]  # Remove alpha channel
        
        elif self._lib_type == 'PIL':
            from PIL import Image
            img = self._screenshot_lib.grab()
            bgr = np.asarray(img).copy()
            return bgr[:,:,:3] if bgr.shape[2] == 4 else bgr
        
        else:  # pyautogui
            img = self._screenshot_lib.screenshot()
            import cv2
            tmp_path = "/tmp/screen.png"
            img.save(tmp_path)
            return cv2.imread(tmp_path)
    
    def capture_region(self, region: dict) -> Tuple[np.ndarray, int, int]:
        """
        Скриншот определённой области экрана.
        
        Args:
            region: {"x": ..., "y": ..., "w": ..., "h": ...}
        
        Returns:
            (bgr_numpy_array, x_offset, y_offset)
        """
        self._ensure_lib()
        
        x_off = region.get("x", 0)
        y_off = region.get("y", 0)
        width = region.get("w", 1280)
        height = region.get("h", 720)
        
        if self._lib_type == 'mss':
            s = self._screenshot_lib
            monitor = {"top": y_off, "left": x_off, 
                      "width": width, "height": height}
            img = s.grab(monitor)
            return np.array(img)[:,:,:3], x_off, y_off
        
        elif self._lib_type == 'PIL':
            bgr = np.asarray(self._screenshot_lib.grab())
            if len(bgr.shape) > 2 and bgr.shape[2] == 4:
                bgr = bgr[:,:,:3]
            region_img = copy_region(bgr, (x_off, y_off, x_off + width, y_off + height))
            return region_img, x_off, y_off
        
        else:  # pyautogui
            import cv2
            tmp_path = "/tmp/region.png"
            self._screenshot_lib.screenshot().save(tmp_path)
            full = cv2.imread(tmp_path)
            if full is None:
                raise RuntimeError("Невозможно сделать скриншот области!")
            region_img = copy_region(full, (x_off, y_off, x_off + width, y_off + height))
            return region_img, x_off, y_off


def copy_region(image: np.ndarray, box: tuple) -> np.ndarray:
    """
    Вырезать область из изображения.
    Args:
        image: BGR numpy array
        box: (left, top, right, bottom)
    Returns:
        Cropped region
    """
    left, top, right, bottom = box
    h, w = image.shape[:2]
    # Clamp to valid range
    left = max(0, left)
    top = max(0, top)
    right = min(w, right)
    bottom = min(h, bottom)
    
    return image[top:bottom, left:right]


def images_equal(img1, img2, tolerance=0.95):
    """Check two screenshots are nearly the same (normalized correlation)"""
    if not isinstance(img1, np.ndarray) or not isinstance(img2, np.ndarray):
        return False
    
    if img1.shape != img2.shape:
        # Resize smaller to match larger
        target_size = max(img1.shape[:2][::-1], img2.shape[:2][::-1])
        img1_r = cv2.resize(img1, target_size)
        img2_r = cv2.resize(img2, target_size)
    else:
        img1_r, img2_r = img1, img2
    
    # Flatten to 1D vectors for correlation
    a = img1_r.flatten().astype(np.float32)
    b = img2_r.flatten().astype(np.float32)
    
    sim = float(np.corrcoef(a, b)[0, 1])
    return sim >= tolerance
