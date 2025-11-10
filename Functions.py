from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Controller as KeyboardController  # Add this line
from pynput import mouse as pynput_mouse, keyboard as pynput_keyboard
import keyboard as kb
import threading
import time
import json
from tkinter import filedialog, messagebox
import os


# Global flag used by start/stop_clicking
is_clicking = False
SETTINGS_FILE = "last_settings.json"

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


def start_global_hotkey_listener(hotkey="F6", toggle_callback=None):
    """
    Register a global hotkey using the 'keyboard' module on a background thread.
    toggle_callback will be called when the hotkey is pressed.
    """
    def listener():
        if toggle_callback:
            kb.add_hotkey(hotkey, toggle_callback)
        else:
            kb.add_hotkey(hotkey, lambda: None)
        kb.wait()

    threading.Thread(target=listener, daemon=True).start()


def start_hotkey_capture(root, on_selected):
    """
    Attach transient bindings to the provided Tk root to capture a keyboard key or mouse button.
    on_selected(selected_string) is called once with a readable string like "Key: Ctrl + q" or "Mouse: Left".
    This does not block the mainloop.
    """
    def on_key_press(event):
        modifiers = []
        if event.state & 0x0001:
            modifiers.append("Shift")
        if event.state & 0x0004:
            modifiers.append("Ctrl")
        if event.state & 0x0008:
            modifiers.append("Alt")
        key_pressed = event.char if event.char else event.keysym
        combo = " + ".join(modifiers + [key_pressed])
        on_selected(f"Key: {combo}")
        root.unbind("<KeyPress>")
        root.unbind("<Button>")

    def on_mouse_click(event):
        button_map = {1: "Left", 2: "Middle", 3: "Right"}
        btn_name = button_map.get(event.num, f"Button {event.num}")
        on_selected(f"Mouse: {btn_name}")
        root.unbind("<KeyPress>")
        root.unbind("<Button>")

    root.bind("<KeyPress>", on_key_press)
    root.bind("<Button>", on_mouse_click)


def pick_position_blocking(root, prompt_message=None):
    """
    Hide root, wait for a mouse click or Esc, restore root and return (x, y) tuple.
    Returns None if cancelled. Blocking — run this from a worker thread if you don't want to freeze UI.
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


