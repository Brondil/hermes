"""Module for performing OCR using Windows built-in APIs via winsdk (Windows) or Mocking (Linux)."""
import cv2
import numpy as np
import os
import tempfile
import asyncio
from typing import List

# Platform check
try:
    import winsdk.windows.graphics.imaging as Imaging
    import winsdk.windows.media.ocr as OCR
    import winsdk.windows.storage as Storage
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

class OCRManager:
    """Handles text extraction from images using Windows Runtime OCR or Mocking mode."""

    def __init__(self, mock_mode: bool = not WINDOWS_AVAILABLE):
        """
        Args:
            mock_mode: If True, returns dummy data. Essential for testing on Linux.
        """
        self.mock_mode = mock_mode or (not WINDOWS_AVAILABLE)
        if self.mock_mode:
            print("OCRManager: RUNNING IN MOCK MODE (Linux/Mock)")
        else:
            print("OCRManager: Running in Windows Native OCR mode.")

    def extract_text(self, image: np.ndarray) -> List[str]:
        """Takes an OpenCV BGR image and returns a list of detected text lines."""
        if self.mock_mode:
            return self._get_mock_rumors()

        # Windows Implementation
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp_path = tmp.name

        try:
            cv2.imwrite(tmp_path, image)
            return self._run_windows_ocr(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _get_mock_rumors(self) -> List[str]:
        """Provides static dummy data for testing logic without hardware dependency."""
        import random
        mock_data = [
            "Refugee from the West",
            "The Light is Fading",
            "Echoes in the Abyss",
            "Gold lies deep beneath",
            "Shadows of the Void",
            "Ancient secrets revealed"
        ]
        # Return one random line to simulate different rumors appearing
        return [random.choice(mock_data)]

    def _run_windows_ocr(self, file_path: str) -> List[str]:
        """Actual WinRT interaction logic for Windows/Winsdk."""
        async def _execute_ocr():
            file = await Storage.StorageFile.get_file_from_path_async(file_path)
            stream = await file.open_async(Storage.FileAccessMode.READ)
            decoder = await Imaging.BitmapDecoder.create_async(stream)
            software_bitmap = await decoder.get_software_bitmap_async()

            engine = OCR.OcrEngine.try_create_from_user_language_profile()
            if not engine:
                return []

            result = await engine.recognize_async(software_bitmap)
            text = str(result.text).strip()
            
            if not text:
                return []

            lines = [line.strip() for line in text.split('\n') if line.strip()]
            return lines

        try:
            # Use a single loop runner to avoid complex async management in UI threads
            return asyncio.run(_execute_ocr())
        except Exception as e:
            print(f"Windows OCR Error (asyncio): {e}")
            return []

