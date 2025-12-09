# Autoclicker.py
# Hotkey manager rewritten to avoid pywin32 (uses keyboard + pynput)

from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from pynput import mouse as pynput_mouse, keyboard as pynput_keyboard
import threading
import time
import json
from tkinter import filedialog, messagebox
import os
import sys
import ctypes
from ctypes import wintypes

_session_monitor_running = False
_session_monitor_handles = {"hwnd": None, "thread": None, "running": False}

# Try to import keyboard module for global hotkeys (pure-Python fallback)
try:
    import keyboard as kb
    _HAS_KEYBOARD = True
except Exception:
    kb = None
    _HAS_KEYBOARD = False
    print("Warning: 'keyboard' module not found. Install with `pip install keyboard` for global hotkeys.")

# --- Settings / Persistence helpers ---
def get_settings_path():
    """Return a safe, writable path for storing user settings."""
    appdata = os.getenv("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(appdata, "AutoClicker")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "last_settings.json")

def save_last_settings(data):
    """Automatically save last used settings."""
    try:
        with open(get_settings_path(), "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to save last settings: {e}")

def load_last_settings():
    """Load last used settings if available."""
    path = get_settings_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load last settings: {e}")
        return None

def save_preset(data):
    """Save current settings to a JSON file via file dialog."""
    filepath = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON Files", "*.json")],
        title="Save Preset As"
    )
    if not filepath:
        return
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=4)
        messagebox.showinfo("Preset Saved", f"Preset saved to:\n{filepath}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save preset:\n{e}")

def load_preset():
    """Load settings from a JSON file via file dialog."""
    filepath = filedialog.askopenfilename(
        filetypes=[("JSON Files", "*.json")],
        title="Load Preset"
    )
    if not filepath:
        return None
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load preset:\n{e}")
        return None

# --- Interval helper (used by GUI.py) ---
def get_total_interval_ms_from_vars(interval_vars):
    """
    Compute total interval in milliseconds from [hours, mins, secs, ms] string vars.
    """
    try:
        hours = int(interval_vars[0].get())
        mins = int(interval_vars[1].get())
        secs = int(interval_vars[2].get())
        millis = int(interval_vars[3].get())
    except Exception:
        return 0
    return hours * 3600000 + mins * 60000 + secs * 1000 + millis

def validate_int_input(value_if_allowed):
    """Tk validation callable for integer-only inputs (disallow empty)."""
    if value_if_allowed == "":
        return False
    return str(value_if_allowed).isdigit()

# --- Clicker logic (unchanged semantic behavior) ---
is_clicking = False

def start_clicking(interval_ms,
                   hotkey=None,
                   on_finish=None,
                   repeat_mode="until_stopped",
                   repeat_times=1,
                   pos_mode="current",
                   x=None,
                   y=None,
                   hold_mode="press",
                   hold_time=0.05):
    """
    Start the click/key loop on a background thread.
    - interval_ms: delay between actions in milliseconds (ignored while in hold mode)
    - hotkey: human-readable string like "Key: Ctrl + q" or "Mouse: Left"
    - on_finish: optional callback invoked when loop naturally finishes (or after release in hold)
    - repeat_mode: "until_stopped" or "repeat"
    """
    global is_clicking
    is_clicking = True
    mouse = MouseController()

    def click_loop():
        i = 0
        kb_controller = KeyboardController()
        mouse_controller = MouseController()
        hold_started = False

        try:
            while is_clicking:
                i += 1
                hk = hotkey.strip().lower() if hotkey else ""

                # Move mouse if requested
                if pos_mode == "pick" and x is not None and y is not None:
                    try:
                        mouse_controller.position = (int(x), int(y))
                    except Exception:
                        pass

                # Mouse actions
                if "mouse" in hk:
                    # Check for scroll actions first
                    if "scroll up" in hk:
                        try:
                            mouse_controller.scroll(0, 1)  # Scroll up (positive delta)
                        except Exception:
                            pass
                    elif "scroll down" in hk:
                        try:
                            mouse_controller.scroll(0, -1)  # Scroll down (negative delta)
                        except Exception:
                            pass
                    else:
                        # Handle button clicks
                        btn = None
                        if "left" in hk:
                            btn = Button.left
                        elif "right" in hk:
                            btn = Button.right
                        elif "middle" in hk:
                            btn = Button.middle
                        elif "button 4" in hk or "x1" in hk:
                            btn = Button.x1
                        elif "button 5" in hk or "x2" in hk:
                            btn = Button.x2

                        if btn:
                            if hold_mode == "press":
                                try:
                                    mouse_controller.press(btn)
                                    time.sleep(hold_time)
                                    mouse_controller.release(btn)
                                except Exception:
                                    pass
                            elif hold_mode == "hold":
                                def hold_mouse():
                                    try:
                                        mouse_controller.press(btn)
                                        while is_clicking:
                                            time.sleep(0.01)
                                    finally:
                                        try:
                                            mouse_controller.release(btn)
                                        except Exception:
                                            pass
                                        if on_finish:
                                            on_finish()

                                threading.Thread(target=hold_mouse, daemon=True).start()
                                hold_started = True
                                break

                # Keyboard actions
                elif hotkey:
                    try:
                        key = hotkey.replace("Key:", "").strip()
                        if "+" in key:
                            parts = [p.strip() for p in key.replace(" + ", "+").split("+")]
                            for part in parts:
                                kb_controller.press(part)
                            if hold_mode == "press":
                                time.sleep(hold_time)
                                for part in reversed(parts):
                                    kb_controller.release(part)
                        else:
                            kb_controller.press(key)
                            if hold_mode == "press":
                                time.sleep(hold_time)
                                kb_controller.release(key)

                        if hold_mode == "hold":
                            break  # Exit loop after first press in hold mode

                    except Exception as e:
                        print(f"Key press failed: {str(e)}")
                        break

                # Repeat termination
                if repeat_mode == "repeat" and i >= repeat_times:
                    break

                # Delay between actions (skip when holding)
                if hold_mode != "hold":
                    time.sleep(max(0, interval_ms / 1000))

        finally:
            if on_finish and not hold_started:
                on_finish()

    threading.Thread(target=click_loop, daemon=True).start()

def stop_clicking():
    """Signal the click loop (and any holder threads) to stop."""
    global is_clicking
    is_clicking = False

# --- Hotkey conversion helpers (display <-> normalized) ---
def convert_to_keyboard_format(hotkey_string):
    """
    Convert hotkey from display format "Key: Alt + s" or "Alt + S" to normalized format "alt+s".
    Also handles simple keys like "F6" -> "f6".
    """
    if not hotkey_string:
        return "f6"

    hotkey = hotkey_string.replace("Key:", "").strip()
    parts = [p.strip() for p in hotkey.replace(" + ", "+").split("+")]

    modifier_map = {
        "ctrl": "ctrl",
        "control": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "win": "win",
        "windows": "win",
        "cmd": "cmd",
        "command": "cmd"
    }

    converted = []
    for p in parts:
        pl = p.lower()
        if pl in modifier_map:
            converted.append(modifier_map[pl])
        else:
            converted.append(pl)
    return "+".join(converted)

def convert_to_display_format(hotkey_string):
    """
    Convert hotkey from normalized format "alt+s" to display format "Alt + S".
    Also handles simple keys like "f6" -> "F6".
    """
    if not hotkey_string:
        return "F6"
    hotkey = hotkey_string.replace("Key:", "").strip()
    parts = [p.strip() for p in hotkey.split("+")]
    display_parts = []
    for part in parts:
        pl = part.lower()
        if pl == "ctrl":
            display_parts.append("Ctrl")
        elif pl == "alt":
            display_parts.append("Alt")
        elif pl == "shift":
            display_parts.append("Shift")
        elif pl in ["win", "windows"]:
            display_parts.append("Win")
        elif pl in ["cmd", "command"]:
            display_parts.append("Cmd")
        else:
            display_parts.append(part.upper())
    return " + ".join(display_parts)

# --- New hotkey manager (keyboard + pynput mouse) ---

# Storage for registered handlers
_keyboard_handlers = {}   # normalized_kb_format -> {'handler': id, 'callback': cb, 'display': display}
_mouse_handlers = {}      # display like "Mouse: Left" -> callback
_mouse_listener = None
_mouse_listener_lock = threading.Lock()

def _ensure_mouse_listener():
    """Ensure a single global mouse listener is running to dispatch mouse button hotkeys."""
    global _mouse_listener
    with _mouse_listener_lock:
        if _mouse_listener and _mouse_listener.running:
            return
        # Start a listener that checks presses and calls matching callbacks
        def on_click(x, y, button, pressed):
            if not pressed:
                return
            # Map Button to display string
            btn_map = {
                Button.left: "Mouse: Left",
                Button.right: "Mouse: Right",
                Button.middle: "Mouse: Middle",
                Button.x1: "Mouse: Button 4",
                Button.x2: "Mouse: Button 5"
            }
            disp = btn_map.get(button)
            if disp and disp in _mouse_handlers:
                try:
                    cb = _mouse_handlers[disp]
                    if cb:
                        threading.Thread(target=cb, daemon=True).start()
                except Exception:
                    pass

        _mouse_listener = pynput_mouse.Listener(on_click=on_click)
        _mouse_listener.daemon = True
        _mouse_listener.start()

def start_global_hotkey_listener(display_hotkey="F6", toggle_callback=None):
    """
    Register a global hotkey. Accepts display string like "F6", "Alt + S", "Key: Ctrl + q", or "Mouse: Left".
    Returns handler info or None on failure.
    """
    if not display_hotkey:
        return None

    display_hotkey = display_hotkey.strip()
    # Mouse handler
    if display_hotkey.lower().startswith("mouse:"):
        # normalize display to canonical casing
        disp = display_hotkey
        # register in mouse handlers dict
        _mouse_handlers[disp] = toggle_callback
        _ensure_mouse_listener()
        return {'type': 'mouse', 'display': disp, 'callback': toggle_callback}

    # Keyboard handler
    if not _HAS_KEYBOARD or not kb:
        print(f"keyboard module not available — cannot register hotkey {display_hotkey}")
        return None

    try:
        kb_format = convert_to_keyboard_format(display_hotkey)
        # Remove existing if present
        if kb_format in _keyboard_handlers:
            try:
                kb.remove_hotkey(_keyboard_handlers[kb_format]['handler'])
            except Exception:
                pass
            del _keyboard_handlers[kb_format]

        # Use keyboard.add_hotkey — it returns an internal handler that can be removed by remove_hotkey
        handler = kb.add_hotkey(kb_format, toggle_callback if toggle_callback else (lambda: None))
        _keyboard_handlers[kb_format] = {'handler': handler, 'callback': toggle_callback, 'display': display_hotkey}
        return _keyboard_handlers[kb_format]
    except Exception as e:
        print(f"Fallback keyboard registration failed for {display_hotkey}: {e}")
        return None

def remove_global_hotkey(display_hotkey="F6"):
    """
    Remove a previously registered hotkey by display string. Returns True if removed.
    """
    if not display_hotkey:
        return False
    display_hotkey = display_hotkey.strip()

    # Mouse remove
    if display_hotkey.lower().startswith("mouse:"):
        if display_hotkey in _mouse_handlers:
            del _mouse_handlers[display_hotkey]
            return True
        # try case-insensitive find
        for k in list(_mouse_handlers.keys()):
            if k.lower() == display_hotkey.lower():
                del _mouse_handlers[k]
                return True
        return False

    # Keyboard remove
    if not _HAS_KEYBOARD or not kb:
        return False

    kb_fmt = convert_to_keyboard_format(display_hotkey)
    # try exact match
    if kb_fmt in _keyboard_handlers:
        try:
            kb.remove_hotkey(_keyboard_handlers[kb_fmt]['handler'])
        except Exception:
            pass
        del _keyboard_handlers[kb_fmt]
        return True

    # try match by display label
    for k, v in list(_keyboard_handlers.items()):
        if v.get('display') == display_hotkey:
            try:
                kb.remove_hotkey(v['handler'])
            except Exception:
                pass
            del _keyboard_handlers[k]
            return True

    # try case-insensitive compare
    for k, v in list(_keyboard_handlers.items()):
        if v.get('display', '').lower() == display_hotkey.lower():
            try:
                kb.remove_hotkey(v['handler'])
            except Exception:
                pass
            del _keyboard_handlers[k]
            return True

    return False

def re_register_all_hotkeys():
    """
    Re-register all currently stored hotkeys (useful after a transient platform event).
    For keyboard: reconstruct registrations from stored snapshot.
    For mouse: listener persists.
    """
    if not _HAS_KEYBOARD or not kb:
        # keyboard module unavailable — nothing to re-register
        return

    # Snapshot current (display, callback) pairs
    snapshot = []
    for fmt, info in list(_keyboard_handlers.items()):
        snapshot.append((info.get('display'), info.get('callback')))

    # Remove everything
    for fmt, info in list(_keyboard_handlers.items()):
        try:
            kb.remove_hotkey(info['handler'])
        except Exception:
            pass
    _keyboard_handlers.clear()

    # Re-register
    for display, callback in snapshot:
        try:
            kb_format = convert_to_keyboard_format(display)
            handler = kb.add_hotkey(kb_format, callback if callback else (lambda: None))
            _keyboard_handlers[kb_format] = {'handler': handler, 'callback': callback, 'display': display}
        except Exception as e:
            print(f"Failed to re-register fallback hotkey {display}: {e}")

# --- Hotkey capture for GUI (Tkinter based) ---
def start_hotkey_capture(root, on_selected):
    """
    Attach transient bindings to the provided Tk root to capture a keyboard key or mouse button.
    on_selected(selected_string) is called once with a readable string like "Key: Ctrl + q" or "Mouse: Left".
    This does not block the mainloop.
    """
    waiting_for_key = {"active": False}
    captured_modifiers = {"list": []}

    modifier_keys = {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
                     "Meta_L", "Meta_R", "Win_L", "Win_R", "Command_L", "Command_R"}

    def on_key_press(event):
        key_pressed = event.keysym

        is_modifier = (key_pressed in modifier_keys or
                       key_pressed in ["Shift", "Control", "Alt", "Meta", "Win", "Command"] or
                       "Shift" in key_pressed or "Control" in key_pressed or
                       "Alt" in key_pressed or "Meta" in key_pressed)

        modifiers = []
        # Detect modifier state via event.state bits (works reliably for common modifiers)
        try:
            if event.state & 0x0001:  # Shift
                modifiers.append("Shift")
            if event.state & 0x0004:  # Ctrl
                modifiers.append("Ctrl")
            if event.state & 0x0008:  # Alt
                modifiers.append("Alt")
        except Exception:
            pass
        if "Meta" in key_pressed or "Win" in key_pressed:
            if "Win" not in modifiers:
                modifiers.append("Win")

        if is_modifier and not waiting_for_key["active"]:
            waiting_for_key["active"] = True
            captured_modifiers["list"] = modifiers.copy()
            return

        if waiting_for_key["active"]:
            final_modifiers = captured_modifiers["list"].copy()
            waiting_for_key["active"] = False
        else:
            final_modifiers = modifiers

        if event.char and event.char.isprintable() and not is_modifier:
            actual_key = event.char
        elif not is_modifier:
            actual_key = event.keysym
            if actual_key.startswith("F") and actual_key[1:].isdigit():
                actual_key = actual_key.upper()
        else:
            return

        if final_modifiers:
            combo = " + ".join(final_modifiers + [actual_key])
        else:
            combo = actual_key

        on_selected(f"Key: {combo}")
        root.unbind("<KeyPress>")
        root.unbind("<Button>")
        root.unbind("<KeyRelease>")
        waiting_for_key["active"] = False
        captured_modifiers["list"] = []

    def on_mouse_click(event):
        button_map = {1: "Left", 2: "Middle", 3: "Right"}
        btn_name = button_map.get(event.num, f"Button {event.num}")
        on_selected(f"Mouse: {btn_name}")
        root.unbind("<KeyPress>")
        root.unbind("<Button>")
        root.unbind("<MouseWheel>")
        root.unbind("<KeyRelease>")
        waiting_for_key["active"] = False
        captured_modifiers["list"] = []

    def on_mouse_scroll(event):
        # Detect scroll direction (positive delta = scroll up, negative = scroll down)
        if event.delta > 0:
            on_selected("Mouse: Scroll Up")
        else:
            on_selected("Mouse: Scroll Down")
        root.unbind("<KeyPress>")
        root.unbind("<Button>")
        root.unbind("<MouseWheel>")
        root.unbind("<KeyRelease>")
        waiting_for_key["active"] = False
        captured_modifiers["list"] = []

    root.bind("<KeyPress>", on_key_press)
    root.bind("<Button>", on_mouse_click)
    root.bind("<MouseWheel>", on_mouse_scroll)

# --- Position picker (pynput based) ---
def pick_position_blocking(root, prompt_message=None):
    """
    Hide root, wait for a mouse click or Esc, restore root and return (x, y) tuple.
    Returns None if cancelled. Blocking - run this from a worker thread if you don't want to freeze UI.
    """
    pos = {"x": None, "y": None, "cancel": False}

    def on_click(x, y, button, pressed):
        if pressed:
            pos["x"], pos["y"] = x, y
            return False

    def on_key_press(key):
        try:
            if key == pynput_keyboard.Key.esc:
                pos["cancel"] = True
                return False
        except Exception:
            pass

    root.withdraw()
    if prompt_message:
        print(prompt_message)

    mouse_listener = pynput_mouse.Listener(on_click=on_click)
    key_listener = pynput_keyboard.Listener(on_press=on_key_press)
    mouse_listener.start()
    key_listener.start()

    # Wait until either listener stops
    while mouse_listener.is_alive() and key_listener.is_alive():
        time.sleep(0.01)

    mouse_listener.stop()
    key_listener.stop()

    root.deiconify()
    root.lift()
    root.focus_force()

    if pos["cancel"]:
        return None
    if pos["x"] is not None and pos["y"] is not None:
        return (int(pos["x"]), int(pos["y"]))
    return None


_session_monitor_running = False
_session_monitor_handles = {"hwnd": None, "thread": None, "running": False}

def start_session_monitor():
    """
    Start a lightweight session monitor that listens for Windows lock/unlock events
    (WM_WTSSESSION_CHANGE). On unlock we call re_register_all_hotkeys() to restore
    keyboard registrations. Silent auto-repair (Option A).
    """
    global _session_monitor_running, _session_monitor_handles

    if _session_monitor_running:
        return
    _session_monitor_running = True

    # Only available on Windows
    if sys.platform != "win32":
        # Fallback: keep the old simple poll monitor to at least try re-registering periodically
        def fallback_monitor():
            last_snapshot = None
            while True:
                try:
                    current_keys = sorted([v.get('display', '') for v in _keyboard_handlers.values()])
                    if current_keys != last_snapshot:
                        time.sleep(0.5)
                        re_register_all_hotkeys()
                        last_snapshot = current_keys
                    time.sleep(3)
                except Exception:
                    time.sleep(2)
        threading.Thread(target=fallback_monitor, daemon=True).start()
        return

    user32 = ctypes.windll.user32
    wtsapi32 = ctypes.windll.wtsapi32
    kernel32 = ctypes.windll.kernel32

    # Constants
    WM_WTSSESSION_CHANGE = 0x02B1
    WTS_SESSION_LOCK = 0x7
    WTS_SESSION_UNLOCK = 0x8
    NOTIFY_FOR_THIS_SESSION = 0  # WTSRegisterSessionNotification flag

    # WNDPROC prototype
    WNDPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)

    class WNDCLASS(ctypes.Structure):
        _fields_ = [
            ("style", ctypes.c_uint),
            ("lpfnWndProc", WNDPROCTYPE),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", ctypes.c_void_p),
            ("hIcon", ctypes.c_void_p),
            ("hCursor", ctypes.c_void_p),
            ("hbrBackground", ctypes.c_void_p),
            ("lpszMenuName", ctypes.c_wchar_p),
            ("lpszClassName", ctypes.c_wchar_p),
        ]

    def _message_thread():
        # Unique class name to avoid collisions
        cls_name = "AutoClickerSessionMonitorWindow"

        # WndProc implementation
        @WNDPROCTYPE
        def _wndproc(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_WTSSESSION_CHANGE:
                    try:
                        ev = int(wparam)
                        # On unlock, rebuild hotkeys quietly
                        if ev == WTS_SESSION_UNLOCK:
                            # small delay to allow desktop to settle
                            time.sleep(0.25)
                            try:
                                re_register_all_hotkeys()
                            except Exception:
                                pass
                    except Exception:
                        pass
                    return 0
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
            except Exception:
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        # Register window class
        hInstance = kernel32.GetModuleHandleW(None)
        wndclass = WNDCLASS()
        wndclass.style = 0
        wndclass.lpfnWndProc = _wndproc
        wndclass.cbClsExtra = 0
        wndclass.cbWndExtra = 0
        wndclass.hInstance = hInstance
        wndclass.hIcon = None
        wndclass.hCursor = None
        wndclass.hbrBackground = None
        wndclass.lpszMenuName = None
        wndclass.lpszClassName = cls_name

        atom = user32.RegisterClassW(ctypes.byref(wndclass))
        if not atom:
            # If registration fails, still attempt the message loop with a default class name
            pass

        # Create message-only window: HWND_MESSAGE (special) is available on Win2000+ as -3
        HWND_MESSAGE = -3
        hwnd = user32.CreateWindowExW(
            0,
            cls_name,
            "AutoClickerSessionMonitor",
            0,
            0, 0, 0, 0,
            HWND_MESSAGE,
            0,
            hInstance,
            None
        )

        if not hwnd:
            # fallback: create a normal hidden window (less ideal) and continue
            hwnd = user32.CreateWindowExW(0, cls_name, "AutoClickerSessionMonitor", 0, 0, 0, 0, 0, 0, 0, hInstance, None)

        # Register for session notifications
        try:
            # BOOL WTSRegisterSessionNotification(HWND hWnd, DWORD dwFlags)
            res = wtsapi32.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION)
            # res==0 -> failure, but we can still run a periodic re-register fallback
        except Exception:
            res = 0

        # Message loop
        msg = wintypes.MSG()
        _session_monitor_handles["hwnd"] = hwnd
        _session_monitor_handles["running"] = True

        while _session_monitor_handles.get("running", False):
            has_msg = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if has_msg == 0:
                break
            if has_msg == -1:
                # error
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup
        try:
            wtsapi32.WTSUnRegisterSessionNotification(hwnd)
        except Exception:
            pass
        try:
            user32.DestroyWindow(hwnd)
        except Exception:
            pass
        _session_monitor_handles["hwnd"] = None
        _session_monitor_handles["running"] = False

    # Start message thread
    t = threading.Thread(target=_message_thread, daemon=True)
    _session_monitor_handles["thread"] = t
    t.start()

    # Also keep a tiny fallback poll to ensure re-register if anything odd happens
    def poll_fallback():
        last_snapshot = None
        while True:
            try:
                current_keys = sorted([v.get('display', '') for v in _keyboard_handlers.values()])
                if current_keys != last_snapshot:
                    time.sleep(0.5)
                    re_register_all_hotkeys()
                    last_snapshot = current_keys
                time.sleep(3)
            except Exception:
                time.sleep(2)

    threading.Thread(target=poll_fallback, daemon=True).start()
# Provide module-level names expected by GUI.py:
# start_clicking, stop_clicking, start_global_hotkey_listener, remove_global_hotkey,
# start_hotkey_capture, pick_position_blocking, validate_int_input,
# get_total_interval_ms_from_vars, save_preset, load_preset, save_last_settings, load_last_settings,
# convert_to_display_format, start_session_monitor

# End of file
