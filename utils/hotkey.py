"""
Hotkey Listener Module - Detects hover and triggers workflow
Ня~ Слушает мышку, ловит триггер (=^･ω･^)
Uses pynput to detect mouse hover on trigger region or F9 press
"""

import time
import threading
from typing import Callable, Optional
from pynput import mouse, keyboard


class HoverListener:
    """
    Ловит наводку мыши на определённую область экрана ИЛИ нажатие хоткея F9, ня~
    
    Два режима:
    1. HOTKEY MODE — нажать F9 чтобы запустить трекер (по умолчанию)
    2. HOVER MODE — мышь попадает в зону триггера и ждёт N секунд => авто-запуск
    """
    
    def __init__(self, trigger_region: tuple = None, 
                 hover_duration: float = 1.5,
                 mode: str = "hotkey"):
        self.trigger_region = trigger_region
        self.hover_duration = hover_duration
        self.mode = mode.lower()
        
        self._on_trigger_cb: Optional[Callable] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._mouse_listener = None
        self._key_listener = None
        
    def set_callback(self, callback: Callable):
        """Установить функцию которая вызывается при срабатывании триггера"""
        self._on_trigger_cb = callback
    
    # ---------- Hotkey mode ----------
    
    def _hotkey_listener(self):
        """Режим хоткея — нажал F9 => запуск"""
        print("[i] Жди нажатие F9 чтобы запустить трекер...")
        with keyboard.Listener(on_press=self._on_key_press) as listener:
            self._key_listener = listener
            listener.join()
    
    def _on_key_press(self, key):
        """Обработчик нажатия клавиши"""
        try:
            if key == keyboard.Key.f9:
                print("[🔥] F9 нажато! Запуск трекинга руморов...")
                self._trigger_once()
        except AttributeError:
            pass
    
    # ---------- Hover mode ----------
    
    def _hover_listener(self):
        """Режим ховера — мышь застыла в зоне триггера => запуск"""
        if not self.trigger_region:
            print("[!] Зона триггера не задана!")
            return
        
        x_start, y_start, w, h = self.trigger_region
        x_end = x_start + w
        y_end = y_start + h
        
        # Mutable state dict so nested functions can modify it
        state = {
            "hover_start_time": None,
            "in_zone": False,
            "triggered": False
        }
        
        def on_move(x, y):
            in_rect = x_start <= x <= x_end and y_start <= y <= y_end
            
            if in_rect and not state["in_zone"]:
                # Just entered zone — start timer
                state["hover_start_time"] = time.time()
                state["in_zone"] = True
                print(f"[i] Мышь в зоне триггера ({w}x{h}), прошло: ", end="", flush=True)
            elif not in_rect and state["in_zone"]:
                # Left zone — reset everything
                state["hover_start_time"] = None
                state["in_zone"] = False
                state["triggered"] = False
                print()  # newline
        
        with mouse.Listener(on_move=on_move) as listener:
            self._mouse_listener = listener
            print(f"[i] Hover режим активен. Зона: ({x_start},{y_start}) {w}x{h}")
            
            while self._running and not state["in_zone"]:
                time.sleep(0.1)
            
            while self._running and state["in_zone"]:
                if state["hover_start_time"] and not state["triggered"]:
                    elapsed = time.time() - state["hover_start_time"]
                    print(f"{elapsed:.1f}s", end="\r", flush=True)
                    
                    if elapsed >= self.hover_duration:
                        print("\n[🔥] Hover сработал! Запуск трекинга...")
                        self._trigger_once()
                        state["triggered"] = True
                        # Reset so it can trigger again
                        time.sleep(0.5)
                        state["hover_start_time"] = None
                        state["in_zone"] = False
                        state["triggered"] = False
                
                time.sleep(0.1)
    
    # ---------- Common ----------
    
    def _trigger_once(self):
        """Вызвать callback один раз (в новом потоке чтобы не блокировать listener)"""
        if self._on_trigger_cb:
            thread = threading.Thread(target=self._on_trigger_cb, daemon=True)
            thread.start()
    
    def start(self):
        """Запустить listener"""
        self._running = True
        
        if self.mode == "hotkey":
            print("[i] Режим: хоткей F9")
            self._hotkey_listener()  # Blocking call
        elif self.mode == "hover":
            print("[i] Режим: hover зона")
            self._hover_listener()  # Blocking call
        else:
            print(f"[!] Неизвестный режим: {self.mode}")
    
    def stop(self):
        """Остановить listener"""
        self._running = False
        if self._mouse_listener:
            self._mouse_listener.stop()
        if self._key_listener:
            self._key_listener.stop()
