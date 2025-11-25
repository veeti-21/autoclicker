from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from pynput import mouse as pynput_mouse, keyboard as pynput_keyboard
import keyboard as kb
import threading
import time
import json
from tkinter import filedialog, messagebox
import os

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Global flag used by start/stop_clicking
is_clicking = False
SETTINGS_FILE = "last_settings.json"
# Store hotkey handlers for removal
_hotkey_handlers = {}

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
    """Save current settings to a JSON file."""
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
    """Load settings from a JSON file."""
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
    - repeat_times: number of repeats when repeat_mode == "repeat"
    - pos_mode: "current" or "pick" (if pick, x and y should be provided)
    - hold_mode: "press" (press+release) or "hold" (keep held until stop)
    - hold_time: seconds to keep key/button pressed in press mode
    """
    global is_clicking
    is_clicking = True
    mouse = MouseController()

    def click_loop():
        i = 0
        kb = KeyboardController()
        mouse = MouseController()
        hold_started = False
        
        try:
            while is_clicking:
                i += 1
                # Define hk before using it
                hk = hotkey.strip().lower() if hotkey else ""
                
                # Move mouse if requested
                if pos_mode == "pick" and x is not None and y is not None:
                    try:
                        mouse.position = (int(x), int(y))
                    except Exception:
                        pass

                # Mouse actions
                if "mouse" in hk:
                    btn = None
                    if "left" in hk:
                        btn = Button.left
                    elif "right" in hk:
                        btn = Button.right
                    elif "middle" in hk:
                        btn = Button.middle
                    elif "button 4" in hk:
                        btn = Button.x1
                    elif "button 5" in hk:
                        btn = Button.x2

                    if btn:
                        if hold_mode == "press":
                            try:
                                mouse.press(btn)
                                time.sleep(hold_time)
                                mouse.release(btn)
                            except Exception:
                                pass
                        elif hold_mode == "hold":
                            def hold_mouse():
                                try:
                                    mouse.press(btn)
                                    while is_clicking:
                                        time.sleep(0.01)
                                finally:
                                    try:
                                        mouse.release(btn)
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
                        # Strip "Key: " prefix and any whitespace
                        key = hotkey.replace("Key:", "").strip()
                        
                        # Handle special characters
                        if "+" in key:
                            # For compound keys like "shift + !"
                            parts = [p.strip() for p in key.split("+")]
                            for part in parts:
                                kb.press(part)
                            
                            if hold_mode == "press":
                                time.sleep(hold_time)
                                for part in reversed(parts):
                                    kb.release(part)
                        else:
                            # For single keys
                            kb.press(key)
                            if hold_mode == "press":
                                time.sleep(hold_time)
                                kb.release(key)
                        
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
            # Ensure click loop flag toggled; holder threads call on_finish themselves
            if on_finish and not hold_started:
                on_finish()

    threading.Thread(target=click_loop, daemon=True).start()

def stop_clicking():
    """Signal the click loop (and any holder threads) to stop."""
    global is_clicking
    is_clicking = False

def convert_to_keyboard_format(hotkey_string):
    """
    Convert hotkey from display format "Key: Alt + s" or "Alt + S" to keyboard module format "alt+s".
    Also handles simple keys like "F6" -> "f6".
    """
    if not hotkey_string:
        return "f6"
    
    # Remove "Key: " prefix if present
    hotkey = hotkey_string.replace("Key:", "").strip()
    
    # Split by " + " or "+" to get parts
    parts = [p.strip() for p in hotkey.replace(" + ", "+").split("+")]
    
    # Convert each part to lowercase for keyboard module
    # Map common modifier names
    modifier_map = {
        "ctrl": "ctrl",
        "control": "ctrl",
        "alt": "alt",
        "shift": "shift",
        "win": "windows",
        "windows": "windows",
        "cmd": "command",
        "command": "command"
    }
    
    converted_parts = []
    for part in parts:
        part_lower = part.lower()
        if part_lower in modifier_map:
            converted_parts.append(modifier_map[part_lower])
        else:
            # For regular keys, just lowercase them
            converted_parts.append(part_lower)
    
    return "+".join(converted_parts)

def convert_to_display_format(hotkey_string):
    """
    Convert hotkey from keyboard module format "alt+s" to display format "Alt + S".
    Also handles simple keys like "f6" -> "F6".
    """
    if not hotkey_string:
        return "F6"
    
    # Remove "Key: " prefix if present
    hotkey = hotkey_string.replace("Key:", "").strip()
    
    # Split by "+" to get parts
    parts = [p.strip() for p in hotkey.split("+")]
    
    # Convert to display format
    display_parts = []
    for part in parts:
        part_lower = part.lower()
        # Capitalize modifiers properly
        if part_lower == "ctrl":
            display_parts.append("Ctrl")
        elif part_lower == "alt":
            display_parts.append("Alt")
        elif part_lower == "shift":
            display_parts.append("Shift")
        elif part_lower in ["win", "windows"]:
            display_parts.append("Win")
        elif part_lower in ["cmd", "command"]:
            display_parts.append("Cmd")
        else:
            # For regular keys, capitalize first letter (F6 -> F6, s -> S)
            if len(part) > 1 and part[0].upper() == part[0]:
                display_parts.append(part.upper() if part.isupper() else part.capitalize())
            else:
                display_parts.append(part.upper())
    
    return " + ".join(display_parts)

def start_global_hotkey_listener(hotkey="F6", toggle_callback=None):
    """
    Register a global hotkey using the 'keyboard' module on a background thread.
    toggle_callback will be called when the hotkey is pressed.
    hotkey can be in display format (e.g., "Alt + S") or keyboard format (e.g., "alt+s").
    Returns the hotkey handler for later removal.
    """
    # Convert to keyboard module format
    keyboard_format = convert_to_keyboard_format(hotkey)
    
    def listener():
        try:
            if toggle_callback:
                handler = kb.add_hotkey(keyboard_format, toggle_callback)
                _hotkey_handlers[hotkey] = handler
                _hotkey_handlers[keyboard_format] = handler  # Also store by keyboard format
            else:
                handler = kb.add_hotkey(keyboard_format, lambda: None)
                _hotkey_handlers[hotkey] = handler
                _hotkey_handlers[keyboard_format] = handler
            kb.wait()
        except Exception as e:
            print(f"Failed to register hotkey {keyboard_format}: {e}")

    threading.Thread(target=listener, daemon=True).start()
    return _hotkey_handlers.get(hotkey) or _hotkey_handlers.get(keyboard_format)

def remove_global_hotkey(hotkey="F6"):
    """
    Remove a global hotkey that was previously registered.
    hotkey can be in display format or keyboard format.
    """
    try:
        # Try both formats
        keyboard_format = convert_to_keyboard_format(hotkey)
        
        # Try to remove by original format
        if hotkey in _hotkey_handlers:
            handler = _hotkey_handlers[hotkey]
            kb.remove_hotkey(handler)
            del _hotkey_handlers[hotkey]
            if keyboard_format in _hotkey_handlers and _hotkey_handlers[keyboard_format] == handler:
                del _hotkey_handlers[keyboard_format]
            return True
        
        # Try to remove by keyboard format
        if keyboard_format in _hotkey_handlers:
            handler = _hotkey_handlers[keyboard_format]
            kb.remove_hotkey(handler)
            del _hotkey_handlers[keyboard_format]
            # Clean up any references to this handler
            keys_to_remove = [k for k, v in _hotkey_handlers.items() if v == handler]
            for k in keys_to_remove:
                del _hotkey_handlers[k]
            return True
    except Exception as e:
        print(f"Failed to remove hotkey {hotkey}: {e}")
    return False

def start_hotkey_capture(root, on_selected):
    """
    Attach transient bindings to the provided Tk root to capture a keyboard key or mouse button.
    on_selected(selected_string) is called once with a readable string like "Key: Ctrl + q" or "Mouse: Left".
    If only a modifier key is pressed, waits for the next key press.
    This does not block the mainloop.
    """
    # Track if we're waiting for a key after a modifier
    waiting_for_key = {"active": False}
    captured_modifiers = {"list": []}
    
    # List of modifier keysyms
    modifier_keys = {"Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", 
                     "Meta_L", "Meta_R", "Win_L", "Win_R", "Command_L", "Command_R"}
    
    def on_key_press(event):
        key_pressed = event.keysym
        
        # Check if this is a modifier key
        is_modifier = (key_pressed in modifier_keys or 
                      key_pressed in ["Shift", "Control", "Alt", "Meta", "Win", "Command"] or
                      "Shift" in key_pressed or "Control" in key_pressed or 
                      "Alt" in key_pressed or "Meta" in key_pressed)
        
        # Get current modifier state from event.state
        modifiers = []
        if event.state & 0x0001:  # Shift
            modifiers.append("Shift")
        if event.state & 0x0004:  # Ctrl
            modifiers.append("Ctrl")
        if event.state & 0x0008:  # Alt
            modifiers.append("Alt")
        # Win key is harder to detect via state, check keysym
        if "Meta" in key_pressed or "Win" in key_pressed:
            if "Win" not in modifiers:
                modifiers.append("Win")
        
        # If only a modifier was pressed, wait for the next key
        if is_modifier and not waiting_for_key["active"]:
            waiting_for_key["active"] = True
            captured_modifiers["list"] = modifiers.copy()
            # Don't unbind, wait for next key
            return
        
        # If we were waiting for a key after modifier, use captured modifiers
        if waiting_for_key["active"]:
            # Use the captured modifiers
            final_modifiers = captured_modifiers["list"].copy()
            waiting_for_key["active"] = False
        else:
            # Use current modifiers
            final_modifiers = modifiers
        
        # Get the actual key (not modifier)
        # Check if it's a printable character
        if event.char and event.char.isprintable() and not is_modifier:
            actual_key = event.char
        elif not is_modifier:
            # Use keysym for non-printable keys like F1-F12, etc.
            actual_key = event.keysym
            # Normalize function keys (F1-F12)
            if actual_key.startswith("F") and actual_key[1:].isdigit():
                actual_key = actual_key.upper()
        else:
            # Still a modifier, wait more
            return
        
        # Build the combination
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
        root.unbind("<KeyRelease>")
        waiting_for_key["active"] = False
        captured_modifiers["list"] = []

    root.bind("<KeyPress>", on_key_press)
    root.bind("<Button>", on_mouse_click)

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
        if key == pynput_keyboard.Key.esc:
            pos["cancel"] = True
            return False

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

def validate_int_input(value_if_allowed):
    """Tk validation callable for integer-only inputs (disallow empty)."""
    if value_if_allowed == "":
        return False
    return str(value_if_allowed).isdigit()

def get_total_interval_ms_from_vars(interval_vars):
    """
    Compute total interval in milliseconds from a list/sequence of objects
    that implement .get() returning strings for [hours, mins, secs, ms].
    """
    try:
        hours = int(interval_vars[0].get())
        mins = int(interval_vars[1].get())
        secs = int(interval_vars[2].get())
        millis = int(interval_vars[3].get())
    except Exception:
        return 0
    return hours * 3600000 + mins * 60000 + secs * 1000 + millis





