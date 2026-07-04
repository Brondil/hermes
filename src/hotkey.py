import sys

class GlobalHotkeyManager:
    def __init__(self, main_app):
        self.main_app = main_app
        # For a real production app we would use keyboard library or Win32 API.
        # In this version, we rely on F8 being handled in the UI loop for simplicity of installation.
