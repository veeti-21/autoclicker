from pynput.mouse import Button, Controller as MouseController
from pynput import mouse as pynput_mouse, keyboard as pynput_keyboard
import keyboard as kb
import threading, time

is_clicking = False

def start_clicking(interval_ms, hotkey=None, on_finish=None,
                   repeat_mode="until_stopped", repeat_times=1,
                   pos_mode="current", x=None, y=None,
                   hold_mode="press", hold_time=0.05):
    """
    Start the clicking / key-pressing loop.
    hold_mode: "press" (press + release) or "hold" (keep held until stop)
    hold_time: only used in press mode
    """

    global is_clicking
    is_clicking = True

    mouse = MouseController()

    print(f"Starting clicker: interval={interval_ms}ms, mode={repeat_mode}, "
          f"count={repeat_times}, hold_mode={hold_mode}, hold_time={hold_time}s, action={hotkey}")

    def click_loop():
        i = 0
        hold_started = False  # track if a separate holder thread was started (so we don't call on_finish twice)
        try:
            while is_clicking:
                i += 1

                # Move to the picked position if needed
                if pos_mode == "pick" and x and y:
                    try:
                        mouse.position = (int(x), int(y))
                    except ValueError:
                        print("Invalid coordinates, skipping move.")

                # --- Parse and execute hotkey ---
                if hotkey:
                    hk = hotkey.strip().lower()

                    # --- Mouse ---
                    if "mouse" in hk:
                        btn = None
                        if "left" in hk: btn = Button.left
                        elif "right" in hk: btn = Button.right
                        elif "middle" in hk: btn = Button.middle
                        elif "button 4" in hk: btn = Button.x1
                        elif "button 5" in hk: btn = Button.x2

                        if btn:
                            if hold_mode == "press":
                                mouse.press(btn)
                                time.sleep(hold_time)
                                mouse.release(btn)
                            elif hold_mode == "hold":
                                # Start a separate holder thread so the click loop doesn't block other listeners
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
                                        # call on_finish here so GUI is updated once release happens
                                        if on_finish:
                                            on_finish()

                                threading.Thread(target=hold_mouse, daemon=True).start()
                                hold_started = True
                                break
                        else:
                            print(f"Unknown mouse button: {hotkey}")

                    # --- Keyboard ---
                    else:
                        # Extract last token after possible modifiers like "ctrl + q"
                        key_name = hk.split(" + ")[-1].strip()

                        # Map some named keys to keyboard library names
                        special_keys = {
                            "space": "space", "enter": "enter", "esc": "esc",
                            "shift": "shift", "ctrl": "ctrl", "alt": "alt",
                            "tab": "tab", "backspace": "backspace",
                        }
                        key_to_press = special_keys.get(key_name, key_name)

                        try:
                            if hold_mode == "press":
                                # use keyboard module for key presses (more compatible with global hooks)
                                kb.press(key_to_press)
                                time.sleep(hold_time)
                                kb.release(key_to_press)
                            elif hold_mode == "hold":
                                # Start a separate holder thread so we don't block other listeners (F6 etc.)
                                def hold_key():
                                    try:
                                        kb.press(key_to_press)
                                        while is_clicking:
                                            time.sleep(0.01)
                                    finally:
                                        try:
                                            kb.release(key_to_press)
                                        except Exception:
                                            pass
                                        if on_finish:
                                            on_finish()

                                threading.Thread(target=hold_key, daemon=True).start()
                                hold_started = True
                                break
                        except Exception as e:
                            print(f"Could not press key '{key_name}': {e}")

                print(f"Action {i}: {hotkey}")

                # Repeat logic
                if repeat_mode == "repeat" and i >= repeat_times:
                    break

                # Wait between actions
                if hold_mode != "hold":  # no interval delay during hold
                    time.sleep(interval_ms / 1000)

        finally:
            print("Clicking stopped.")
            # If we started a holder thread, that thread is responsible for calling on_finish after releasing.
            if on_finish and not hold_started:
                on_finish()

    threading.Thread(target=click_loop, daemon=True).start()


def stop_clicking():
    global is_clicking
    is_clicking = False


# ---- New helper functions to move to functions.py ----

def start_global_hotkey_listener(hotkey="F6", toggle_callback=None):
    """Start a background thread that registers a global hotkey and calls toggle_callback."""
    def listener():
        if toggle_callback:
            kb.add_hotkey(hotkey, toggle_callback)
        else:
            kb.add_hotkey(hotkey, lambda: None)
        kb.wait()  # block this thread forever
    threading.Thread(target=listener, daemon=True).start()

def start_hotkey_capture(root, on_selected):
    """
    Attach transient bindings to 'root' to capture a keyboard key or mouse button.
    on_selected(selected_string) is called once with a readable string like "Ctrl + q" or "Mouse: Left".
    """
    def on_key_press(event):
        modifiers = []
        if event.state & 0x0001: modifiers.append("Shift")
        if event.state & 0x0004: modifiers.append("Ctrl")
        if event.state & 0x0008: modifiers.append("Alt")
        key_pressed = event.char if event.char else event.keysym
        combo = " + ".join(modifiers + [key_pressed])
        on_selected(f"Key: {combo}")
        root.unbind("<KeyPress>"); root.unbind("<Button>")

    def on_mouse_click(event):
        button_map = {1: "Left", 2: "Middle", 3: "Right"}
        btn_name = button_map.get(event.num, f"Button {event.num}")
        on_selected(f"Mouse: {btn_name}")
        root.unbind("<KeyPress>"); root.unbind("<Button>")

    root.bind("<KeyPress>", on_key_press)
    root.bind("<Button>", on_mouse_click)

def pick_position_blocking(root, prompt_message=None):
    """
    Hide root, wait for a mouse click or Esc, return (x,y) or None if canceled.
    Blocking; run on a thread that doesn't block the Tk mainloop if you need.
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
    mouse_listener.start(); key_listener.start()
    # Wait until either listener stops
    while mouse_listener.is_alive() and key_listener.is_alive():
        time.sleep(0.01)
    mouse_listener.stop(); key_listener.stop()
    root.deiconify(); root.lift(); root.focus_force()
    if pos["cancel"]:
        return None
    if pos["x"] is not None and pos["y"] is not None:
        return (int(pos["x"]), int(pos["y"]))
    return None

def validate_int_input(value_if_allowed):
    """Tk validation callable for integer-only inputs (disallow empty)."""
    if value_if_allowed == "":
        return False
    return value_if_allowed.isdigit()

def get_total_interval_ms_from_vars(interval_vars):
    """Compute total interval (ms) from a list of StringVar-like objects in order [h,m,s,ms]."""
    try:
        hours = int(interval_vars[0].get())
        mins = int(interval_vars[1].get())
        secs = int(interval_vars[2].get())
        millis = int(interval_vars[3].get())
    except Exception:
        return 0
    return hours*3600000 + mins*60000 + secs*1000 + millis
