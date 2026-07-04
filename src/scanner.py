import time
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, QRect
import pyautogui

from src.config import Config
from src.screenshot import ScreenshotManager
from src.preprocess import ImagePreprocessor
from src.ocr import OCRManager
from src.fuzzy import FuzzyHashSet
from src.cleaner import TextCleaner

class ScannerWorker(QThread):
    \"\"\"The background worker that handles the heavy scanning loop without freezing the UI.\"\"\"
    rumor_found = pyqtSignal(str)  # Emits when a NEW unique rumor is detected
    count_changed = pyqtSignal(int) # Emits current total count
    error_occurred = pyqtSignal(str)
    status_msg = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.is_running = False
        self._roi_norm = (0.0, 0.0, 0.0, 0.0)  # x, y, w, h as % of screen
        
        # Logic Modules
        self.config = Config()
        self.screenshot_manager = ScreenshotManager()
        self.preprocessor = ImagePreprocessor()
        self.ocr_manager = OCRManager()
        self.cleaner = TextCleaner()
        self.rumor_set = FuzzyHashSet(threshold=0.85)

    def set_roi(self, screen_geometry: QRect):
        \"\"\"Converts raw pixel coordinates to percentage-based ROI for resolution independence.\"\"\"
        # We derive normalization based on current desktop size to keep it stable if player changes res later
        sw, sh = pyautogui.size()
        if sw <= 0 or sh <= 0:
            self._roi_norm = (0.0, 0.0, 1.0, 1.0)
            return

        self._roi_norm = (
            float(screen_geometry.x()) / float(sw),
            float(screen_geometry.y()) / float(sh),
            float(screen_geometry.width()) / float(sw),
            float(screen_geometry.height()) / float(sh)
        )
        print(f"Scanner: ROI normalized (0-1): {self._roi_norm}")

    def _get_pixel_rect(self, current_monitor_w: int, current_monitor_h: int) -> QRect:
        \"\"\"Converts normalized ROI back to actual pixels for the current monitor size.\"\"\"
        x = int(self._roi_norm[0] * current_monitor_w)
        y = int(self._roi_norm[1] * current_monitor_h)
        w = int(self._roi_norm[2] * current_monitor_w)
        h = int(self._roi_norm[3] * current_monitor_h)
        return QRect(x, y, w, h)

    def stop(self):
        self.is_running = False
        if self.isRunning():
            self.wait() 

    def run(self):
        \"\"\"Main loop executed in background thread.\"\"\"
        print(\"Scanner Thread: Starting... nya! (=^･ωﾟ･=)\")
        self.is_running = True
        self.rumor_set.reset()
        last_hash = None

        try:
            while self.is_running:
                start_time = time.time()
                
                # 1. Capture ROI (Get current screen size for scaling)
                sw, sh = pyautogui.size()
                target_rect = self._get_pixel_rect(sw, sh)

                captured_img, _ = self.screenshot_manager.get_roi_capture(target_rect)
                if captured_img is None:
                    time.sleep(0.5)
                    continue

                # 2. Check for visual change (Hash Optimization)
                current_hash = self._calculate_image_hash(captured_img)
                new_rumors_this_tick = []

                if current_hash != last_hash:
                    last_hash = current_hash
                    
                    # 3. Preprocess
                    processed_img = self.preprocessor.prepare_for_ocr(captured_img)
                    
                    # 4. OCR Extraction
                    raw_lines = self.ocr_manager.extract_text(processed_img)
                    
                    # 5. Deduplication and Fuzzy Matching
                    for line in raw_lines:
                        clean_line = self.cleaner.clean(line)
                        if not clean_line:
                            continue
                        
                        is_new, _ = self.rumor_set.add(clean_line)
                        if is_new:
                            new_rumors_this_tick.append(clean_line)

                # 6. UI Communication
                if new_rumors_this_tick:
                    self.count_changed.emit(len(self.rumor_set))
                    for r in new_rumors_this_tick:
                        self.rumor_found.emit(r)

                # 7. Throttling (~1Hz)
                elapsed = time.time() - start_time
                sleep_time = max(0.1, 1.0 - elapsed)
                time.sleep(sleep_time)
        except Exception as e:
            self.error_occurred.emit(str(e))
            print(f"Scanner Thread Error: {e}")
        finally:
            self.is_running = False
            print(\"Scanner Thread: Stopped. (=^‥^=)\")

    def _calculate_image_hash(self, img):
        \"\"\"Quick perceptual hash to detect if anything on screen actually changed.\"\"\"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (16, 12), interpolation=cv2.INTER_AREA)
        _, thresh = cv2.threshold(resized, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        return hash(thresh.tobytes())
