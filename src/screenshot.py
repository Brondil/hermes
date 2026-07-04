import cv2
import numpy as np
from mss import mss

class ScreenshotManager:
    def __init__(self):
        self.sct = mss()

    def get_roi_capture(self, rect):
        bbox = {
            'top': rect.y(),
            'left': rect.x(),
            'width': rect.width(),
            'height': rect.height()
        }
        sct_img = self.sct.grab(bbox)
        img = np.array(sct_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img, rect
