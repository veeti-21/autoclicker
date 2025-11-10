import threading
import tkinter as tk
from tkinter import ttk

# Try package-relative import (works when run as module). Fall back to direct import (works when run as script).
try:
    from .functions import (
        start_clicking, stop_clicking,
        start_global_hotkey_listener, start_hotkey_capture,
        pick_position_blocking, validate_int_input, get_total_interval_ms_from_vars,
        save_preset, load_preset
    )
except (ImportError, ValueError):
    from functions import (
        start_clicking, stop_clicking,
        start_global_hotkey_listener, start_hotkey_capture,
        pick_position_blocking, validate_int_input, get_total_interval_ms_from_vars,
        save_preset, load_preset
    )

root = tk.Tk()
root.title("Auto Clicker")
root.geometry("415x400")
root.resizable(False, False)

# === Always on Top (Pin) Option ===
pin_var = tk.BooleanVar(value=False)

def toggle_pin():
    root.attributes('-topmost', pin_var.get())

frame_pin = ttk.Frame(root)
frame_pin.pack(fill="x", padx=10, pady=3)

pin_checkbox = ttk.Checkbutton(
    frame_pin,
    text="Pin window",
    variable=pin_var,
    command=toggle_pin
)
pin_checkbox.pack(anchor="w")


clicker_running = {"active": False}

def toggle_clicker():
    """Called by global hotkey (F6)."""
    if clicker_running["active"]:
        on_click_stop()
    else:
        on_click_start()

# start global hotkey listener (runs background thread inside functions.start_global_hotkey_listener)
start_global_hotkey_listener("F6", toggle_clicker)

def on_click_start():
    clicker_running["active"] = True
    interval_ms = get_total_interval_ms()

    # disable UI (keeps Stop enabled)
    set_running_mode(True)

    # optional: keep explicit states for start/stop buttons consistent
    btn_start.config(state="disabled")
    btn_stop.config(state="normal")

    mode = repeat_var.get()
    count = int(spin_times.get()) if mode == "repeat" else 1

    pos_mode = pos_var.get()
    x = x_var.get()
    y = y_var.get()

    try:
        hold_time_ms = float(hold_time_var.get()) if hold_time_var.get() else 50
    except Exception:
        hold_time_ms = 50

    start_clicking(
        interval_ms,
        hotkey=selected_hotkey["key"],
        on_finish=on_click_stop_done,
        repeat_mode=mode,
        repeat_times=count,
        pos_mode=pos_mode,
        x=x,
        y=y,
        hold_mode=hold_mode_var.get(),
        hold_time=hold_time_ms / 1000
    )

def on_click_stop():
    clicker_running["active"] = False
    stop_clicking()
    btn_start.config(state="normal")
    btn_stop.config(state="disabled")
    set_running_mode(False)   # re-enable UI

def on_click_stop_done():
    set_running_mode(False)
    btn_start.config(state="normal")
    btn_stop.config(state="disabled")

# ==== Click Interval ====
frame_interval = ttk.LabelFrame(root, text="Click interval")
frame_interval.pack(fill="x", padx=10, pady=5)

# Register validation from functions module
vcmd = (root.register(validate_int_input), "%P")

interval_labels = ["hours", "mins", "secs", "milliseconds"]
interval_vars = []

for i, lbl in enumerate(interval_labels):
    default_val = "0" if lbl != "milliseconds" else "100"
    v = tk.StringVar(value=default_val)
    interval_vars.append(v)

    entry = ttk.Entry(
        frame_interval,
        textvariable=v,
        width=5,
        validate="key",
        validatecommand=vcmd
    )
    entry.grid(row=0, column=i*2, padx=3, pady=3)

    ttk.Label(frame_interval, text=lbl).grid(row=0, column=i*2+1, padx=3)

def get_total_interval_ms():
    return get_total_interval_ms_from_vars(interval_vars)

# ==== Click Options ====
frame_options = ttk.LabelFrame(root, text="Click options")
frame_options.pack(fill="x", padx=10, pady=5)

ttk.Label(frame_options, text="Hotkey:").grid(row=2, column=0, padx=5, pady=5, sticky="w")

hotkey_var = tk.StringVar(value="None")
entry_hotkey = ttk.Entry(frame_options, textvariable=hotkey_var, width=20)  # Remove state="readonly"
entry_hotkey.grid(row=2, column=1, padx=5, pady=5)

# Add validation when manually entering hotkey
def on_hotkey_changed(*args):
    entered_key = hotkey_var.get().strip()
    if entered_key.lower() == "none":
        selected_hotkey["key"] = None
        return
        
    # Handle special characters and modifiers
    if entered_key and not entered_key.lower().startswith(("key:", "mouse:")):
        hotkey_var.set(f"Key: {entered_key}")
    
    selected_hotkey["key"] = hotkey_var.get()

hotkey_var.trace_add("write", on_hotkey_changed)

is_listening_for_hotkey = {"active": False}
selected_hotkey = {"key": None}

def start_hotkey_listen():
    """Activate capturing via the shared helper in functions.py"""
    if is_listening_for_hotkey["active"]:
        return
    is_listening_for_hotkey["active"] = True
    hotkey_var.set("Press any key or mouse button...")

    def on_selected(selected_string):
        # Handle shift + special character combinations
        if "shift" in selected_string.lower() and any(char in selected_string for char in '!@#$%^&*()_+{}|:"<>?~'):
            selected_string = selected_string.replace("Key: ", "Key: shift + ")
            
        selected_hotkey["key"] = selected_string
        hotkey_var.set(selected_string)
        is_listening_for_hotkey["active"] = False

    start_hotkey_capture(root, on_selected)

ttk.Button(frame_options, text="Set Hotkey", width=15, command=start_hotkey_listen).grid(row=2, column=2, padx=5, pady=5)

# ==== Click Repeat ====
frame_repeat = ttk.LabelFrame(root, text="Click repeat")
frame_repeat.pack(fill="x", padx=10, pady=5)

repeat_var = tk.StringVar(value="until_stopped")
repeat_count = tk.StringVar(value="1")

ttk.Radiobutton(frame_repeat, text="Repeat", variable=repeat_var, value="repeat").grid(
    row=0, column=0, sticky="w", padx=5
)
spin_times = tk.Spinbox(frame_repeat, from_=1, to=1000, textvariable=repeat_count, width=5, state="disabled")
spin_times.grid(row=0, column=1)
ttk.Label(frame_repeat, text="times").grid(row=0, column=2, sticky="w")

ttk.Radiobutton(frame_repeat, text="Repeat until stopped", variable=repeat_var, value="until_stopped").grid(
    row=1, column=0, columnspan=3, sticky="w", padx=5
)

def update_repeat_state(*args):
    spin_times.config(state="normal" if repeat_var.get() == "repeat" else "disabled")
repeat_var.trace_add("write", update_repeat_state)

hold_mode_var = tk.StringVar(value="press")
ttk.Radiobutton(frame_repeat, text="Press", variable=hold_mode_var, value="press").grid(row=0, column=3, sticky="w", padx=(20, 2))

hold_time_var = tk.DoubleVar(value=50)
spin_hold = tk.Spinbox(frame_repeat, from_=1, to=2000, increment=10, textvariable=hold_time_var, width=5)
spin_hold.grid(row=0, column=4, padx=(2, 2))
ttk.Label(frame_repeat, text="ms").grid(row=0, column=5, sticky="w", padx=(2, 5))

ttk.Radiobutton(frame_repeat, text="Hold down", variable=hold_mode_var, value="hold").grid(row=1, column=3, columnspan=3, sticky="w", padx=(20, 5))

# ==== Cursor Position ====
def pick_position():
    """Run blocking pick on a worker thread and update UI via root.after."""
    def worker():
        res = pick_position_blocking(root, prompt_message="Click anywhere to set position, or press Esc to cancel...")
        def apply_result():
            if res is None:
                return
            x_val, y_val = res
            x_var.set(str(x_val))
            y_var.set(str(y_val))
            pos_var.set("pick")
        root.after(0, apply_result)
    threading.Thread(target=worker, daemon=True).start()

frame_cursor = ttk.LabelFrame(root, text="Cursor position")
frame_cursor.pack(fill="x", padx=10, pady=5)

pos_var = tk.StringVar(value="current")
x_var = tk.StringVar(value="0")    # Add this
y_var = tk.StringVar(value="0")    # Add this

ttk.Radiobutton(frame_cursor, text="Current location", variable=pos_var, value="current").grid(row=0, column=0, sticky="w", padx=5)
ttk.Radiobutton(frame_cursor, text="Pick location", variable=pos_var, value="pick").grid(row=0, column=1, sticky="w", padx=5)

# Add Pick button next to radio buttons
ttk.Button(frame_cursor, text="Pick", command=pick_position, width=8).grid(row=0, column=2, sticky="w", padx=5)

ttk.Label(frame_cursor, text="X").grid(row=0, column=3)
entry_x = tk.Entry(frame_cursor, width=5, textvariable=x_var)
entry_x.grid(row=0, column=4)
ttk.Label(frame_cursor, text="Y").grid(row=0, column=5)
entry_y = tk.Entry(frame_cursor, width=5, textvariable=y_var)
entry_y.grid(row=0, column=6)

# ==== Buttons ====
frame_buttons = tk.Frame(root)
frame_buttons.pack(pady=10)

btn_start = ttk.Button(frame_buttons, text="Start (F6)", width=18, command=on_click_start)
btn_start.grid(row=0, column=0, padx=5, pady=5)

btn_stop = ttk.Button(frame_buttons, text="Stop (F6)", width=18, command=on_click_stop, state="disabled")
btn_stop.grid(row=0, column=1, padx=5, pady=5)
def on_save_preset():
    data = {
        "interval": {lbl: interval_vars[i].get() for i, lbl in enumerate(interval_labels)},
        "repeat_mode": repeat_var.get(),
        "repeat_count": repeat_count.get(),
        "hold_mode": hold_mode_var.get(),
        "hold_time": hold_time_var.get(),
        "pos_mode": pos_var.get(),
        "x": x_var.get(),
        "y": y_var.get(),
        "hotkey": selected_hotkey["key"]
    }
    save_preset(data)

def on_load_preset():
    preset = load_preset()
    if not preset:
        return

    for i, lbl in enumerate(interval_labels):
        interval_vars[i].set(preset["interval"].get(lbl, "0"))
    repeat_var.set(preset.get("repeat_mode", "until_stopped"))
    repeat_count.set(preset.get("repeat_count", "1"))
    hold_mode_var.set(preset.get("hold_mode", "press"))
    hold_time_var.set(preset.get("hold_time", 50))
    pos_var.set(preset.get("pos_mode", "current"))
    x_var.set(preset.get("x", "0"))
    y_var.set(preset.get("y", "0"))
    selected_hotkey["key"] = preset.get("hotkey")
    if selected_hotkey["key"]:
        hotkey_var.set(selected_hotkey["key"])

# --- Preset Buttons (below Start/Stop) ---
btn_save_preset = ttk.Button(frame_buttons, text="Save Preset", width=18, command=on_save_preset)
btn_save_preset.grid(row=1, column=0, padx=5, pady=2)

btn_load_preset = ttk.Button(frame_buttons, text="Load Preset", width=18, command=on_load_preset)
btn_load_preset.grid(row=1, column=1, padx=5, pady=2)

# Helpers to disable/enable all interactive widgets except the Stop button
def set_running_mode(running: bool):
    """
    When running==True: disable all interactive widgets except btn_stop (which stays enabled).
    When running==False: re-enable widgets and disable btn_stop.
    """
    def recurse(widget):
        for child in widget.winfo_children():
            # Ensure the Stop button remains enabled while running
            if child is btn_stop:
                try:
                    child.config(state="normal" if running else "disabled")
                except Exception:
                    pass
            else:
                try:
                    # Try the common 'state' configuration; ignore widgets that don't support it
                    child.configure(state="disabled" if running else "normal")
                except Exception:
                    pass
            recurse(child)
    recurse(root)

# Prevent window close while running; allow close when stopped
def _on_close():
    if clicker_running.get("active"):
        return
    root.destroy()

root.protocol("WM_DELETE_WINDOW", _on_close)

root.mainloop()
