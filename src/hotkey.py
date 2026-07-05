# -*- coding: utf-8 -*-
"""Global hotkey handler for PoE2 Rumor Counter on Windows.

Uses ctypes to bind directly to user32.dll — no pip-installed pywin32
dependency (which is notoriously hard on Python 3.10+).

Supported keys in this version:
    F8 => stop / restart scanner

If the platform is not Windows, import returns silently and all
methods are safe-no-ops so nothing crashes.
"""
import sys


# ------------------------------------------------------------------ #
# Stub for non-Windows platforms
# ------------------------------------------------------------------ #
if sys.platform != "win32":
    class GlobalHotkeyManager:
        """No-op stub – hotkeys never work outside Windows."""

        def __init__(self, main_app):
            self.main_app = main_app
            print("GlobalHotkey: Not on Windows. Hotkeys are disabled.")

        def register(self):
            pass

        def unregister(self):
            pass


# ------------------------------------------------------------------ #
# Full Win32 implementation
# ------------------------------------------------------------------ #
__all__ = ["GlobalHotkeyManager"]


def _make_win32_manager():
    """Factory to return a win32-based GlobalHotkeyManager."""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # RegisterHotKey(hwnd, id, fsModifiers, vk) -> non-zero if success
    user32.RegisterHotKey.argtypes = [
        wintypes.HWND,       # hWnd
        wintypes.INT,        # id
        wintypes.UINT,       # fsModifiers
        wintypes.UINT,       # vk
    ]
    user32.RegisterHotKey.restype = wintypes.BOOL

    class GlobalHotkeyManager:
        """Register a global Win32 hotkey and call main_app.on_hotkey(key) when pressed."""

        HOTKEY_ID = 0xF800      # arbitrary unique ID for our app
        MOD_KEY   = 0x0400       # MOD_KEYDOWN (fires when key is first pressed, not repeat)

        def __init__(self, main_app):
            self.main_app = main_app
            self._registered = False

        @property
        def is_registered(self) -> bool:
            return self._registered

        def register(self):
            """Register F8 as global hotkey."""
            success = user32.RegisterHotKey(
                None,       # monitor all windows (desktop-level)
                self.HOTKEY_ID,
                self.MOD_KEY,
                0x77,       # virtual-key code for F8
            )
            if not success:
                err = ctypes.get_last_error()
                print(f"GlobalHotkey: RegisterHotKey failed (error {err})")
                return False

            self._registered = True
            print("GlobalHotkey: F8 registered successfully.")
            return True

        def unregister(self):
            """Unregister the hotkey."""
            if not self._registered:
                return
            user32.UnregisterHotKey(None, self.HOTKEY_ID)
            self._registered = False

        def is_key(self, vk_code: int) -> bool:
            """Check if a key message corresponds to our hotkey."""
            return vk_code == 0x77   # F8

    return GlobalHotkeyManager


class GlobalHotkeyManager:
    """Dispatches based on platform at import time."""
    pass  # see _make_win32_manager assignment below


# Apply the right class now, not later
_instance = _make_win32_manager() if sys.platform == "win32" else None
if callable(_instance):
    GlobalHotkeyManager = _instance  # type: ignore[assignment]
