import threading,keyboard,time,pyautogui,tkinter as tk
from pynput import mouse, keyboard as kb
from tkinter import ttk
from Functions import start_clicking, stop_clicking

root = tk.Tk()
root.title("Auto Clicker")
root.geometry("500x400")
root.resizable(False, False)

clicker_running = {"active": False}

def toggle_clicker():
    """Called when F6 is pressed globally."""
    if clicker_running["active"]:
        print("Stop hotkey pressed (F6)")
        on_click_stop()
        # optionally re-enable GUI buttons here if needed
    else:
        print("Start hotkey pressed (F6)")
        on_click_start()
        

def listen_for_hotkeys():
    """Run global hotkey listener in background thread."""
    keyboard.add_hotkey("F6", toggle_clicker)
    keyboard.wait()  # block this thread forever

threading.Thread(target=listen_for_hotkeys, daemon=True).start()

def on_click_start():
    clicker_running["active"] = True
    interval_ms = get_total_interval_ms()

    # Disable start and enable stop
    btn_start.config(state="disabled")
    btn_stop.config(state="normal")

    # Get repeat settings
    mode = repeat_var.get()  # "repeat" or "until_stopped"
    count = int(spin_times.get()) if mode == "repeat" else 1  # use spin_times instead of repeat_count

    # Get cursor position settings
    pos_mode = pos_var.get()  # "current" or "pick"
    x = x_var.get()
    y = y_var.get()
    
    try:
        hold_time_ms = float(hold_time_var.get()) if hold_time_var.get() else 50
    except Exception:
        hold_time_ms = 50  # fallback in case of invalid input
        
    # Pass everything to start_clicking
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
    hold_time=hold_time_ms / 1000  # convert ms → seconds
)

    # disable GUI controls while running



def on_click_stop():
    clicker_running["active"] = False
    stop_clicking()
    # Immediately toggle buttons
    btn_start.config(state="normal")
    btn_stop.config(state="disabled")
    # re-enable GUI controls



def on_click_stop_done():
    # Called when click loop finishes on its own
    btn_start.config(state="normal")
    btn_stop.config(state="disabled")
    # re-enable GUI controls

    
# ==== Click Interval ====
frame_interval = ttk.LabelFrame(root, text="Click interval")
frame_interval.pack(fill="x", padx=10, pady=5)

# Create a validation function
def validate_int_input(value_if_allowed):
    """
    Allow only digits, disallow empty string.
    """
    if value_if_allowed == "":
        return False  # disallow empty input
    return value_if_allowed.isdigit()

# Register it with Tkinter (returns a callable reference)
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
        validate="key",           # trigger validation on each keystroke
        validatecommand=vcmd      # link to our validation function
    )
    entry.grid(row=0, column=i*2, padx=3, pady=3)

    ttk.Label(frame_interval, text=lbl).grid(row=0, column=i*2+1, padx=3)

def get_total_interval_ms():
    try:
        hours = int(interval_vars[0].get())
        mins = int(interval_vars[1].get())
        secs = int(interval_vars[2].get())
        millis = int(interval_vars[3].get())
    except ValueError:
        return 0
    return hours*3600000 + mins*60000 + secs*1000 + millis

# ==== Click Options ====
frame_options = ttk.LabelFrame(root, text="Click options")
frame_options.pack(fill="x", padx=10, pady=5)

# --- Hotkey setup ---
ttk.Label(frame_options, text="Hotkey:").grid(row=2, column=0, padx=5, pady=5, sticky="w")

hotkey_var = tk.StringVar(value="None")
entry_hotkey = ttk.Entry(frame_options, textvariable=hotkey_var, width=20, state="readonly")
entry_hotkey.grid(row=2, column=1, padx=5, pady=5)

# --- State tracking ---
is_listening_for_hotkey = {"active": False}
selected_hotkey = {"key": None}  # <-- this stores the chosen key OR mouse

def start_hotkey_listen():
    """Activate hotkey capture mode."""
    if is_listening_for_hotkey["active"]:
        return
    is_listening_for_hotkey["active"] = True
    hotkey_var.set("Press any key or mouse button...")
    root.bind("<KeyPress>", on_key_press)
    root.bind("<Button>", on_mouse_click)

def stop_hotkey_listen():
    """Stop listening for hotkey."""
    if not is_listening_for_hotkey["active"]:
        return
    is_listening_for_hotkey["active"] = False
    root.unbind("<KeyPress>")
    root.unbind("<Button>")

def on_key_press(event):
    if not is_listening_for_hotkey["active"]:
        return

    modifiers = []
    if event.state & 0x0001:
        modifiers.append("Shift")
    if event.state & 0x0004:
        modifiers.append("Ctrl")
    if event.state & 0x0008:
        modifiers.append("Alt")

    key_pressed = event.char if event.char else event.keysym
    combo = " + ".join(modifiers + [key_pressed])
    hotkey_var.set(f"Key: {combo}")

    selected_hotkey["key"] = combo  # ✅ store selected hotkey (keyboard)
    stop_hotkey_listen()

def on_mouse_click(event):
    """Handle mouse button press."""
    if not is_listening_for_hotkey["active"]:
        return

    button_map = {1: "Left", 2: "Middle", 3: "Right"}
    btn_name = button_map.get(event.num, f"Button {event.num}")
    hotkey_var.set(f"Mouse: {btn_name}")

    selected_hotkey["key"] = f"Mouse: {btn_name}"  # ✅ now also store mouse hotkey
    stop_hotkey_listen()

# --- Button to activate hotkey capture ---
ttk.Button(frame_options, text="Set Hotkey", width=15, command=start_hotkey_listen).grid(row=2, column=2, padx=5, pady=5)

# ==== Click Repeat ====
frame_repeat = ttk.LabelFrame(root, text="Click repeat")
frame_repeat.pack(fill="x", padx=10, pady=5)

repeat_var = tk.StringVar(value="until_stopped")
repeat_count = tk.StringVar(value="1")

# --- Left side (repeat options) ---
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

# --- Right side (hold options) ---

# stacked vertically (like Repeat section)

hold_mode_var = tk.StringVar(value="press")

# "Press" radio right next to the Spinbox
ttk.Radiobutton(
    frame_repeat, text="Press", variable=hold_mode_var, value="press"
).grid(row=0, column=3, sticky="w", padx=(20, 2))

# Spinbox directly after it
hold_time_var = tk.DoubleVar(value=50)
spin_hold = tk.Spinbox(
    frame_repeat, from_=1, to=2000, increment=10,
    textvariable=hold_time_var, width=5
)
spin_hold.grid(row=0, column=4, padx=(2, 2))

# “ms” label immediately after
ttk.Label(frame_repeat, text="ms").grid(row=0, column=5, sticky="w", padx=(2, 5))

# Second line: “Hold down”
ttk.Radiobutton(
    frame_repeat, text="Hold down", variable=hold_mode_var, value="hold"
).grid(row=1, column=3, columnspan=3, sticky="w", padx=(20, 5))

# ==== Cursor Position ====
frame_cursor = ttk.LabelFrame(root, text="Cursor position")
frame_cursor.pack(fill="x", padx=10, pady=5)

pos_var = tk.StringVar(value="current")

# --- radio buttons ---
ttk.Radiobutton(
    frame_cursor, text="Current location",
    variable=pos_var, value="current"
).grid(row=0, column=0, sticky="w", padx=5)

ttk.Radiobutton(
    frame_cursor, text="Pick location",
    variable=pos_var, value="pick"
).grid(row=0, column=1, sticky="w", padx=5)

# --- coordinate inputs ---
x_var = tk.StringVar(value="")
y_var = tk.StringVar(value="")

ttk.Label(frame_cursor, text="X").grid(row=0, column=2)
entry_x = tk.Entry(frame_cursor, width=5, textvariable=x_var)
entry_x.grid(row=0, column=3)

ttk.Label(frame_cursor, text="Y").grid(row=0, column=4)
entry_y = tk.Entry(frame_cursor, width=5, textvariable=y_var)
entry_y.grid(row=0, column=5)

# --- Pick position function ---
def pick_position():
    """Hide GUI, wait for mouse click or Esc, then restore and fill X/Y."""
    pos = {"x": None, "y": None, "cancel": False}

    def on_click(x, y, button, pressed):
        if pressed:
            pos["x"], pos["y"] = x, y
            return False  # stop listener

    def on_key_press(key):
        if key == kb.Key.esc:
            pos["cancel"] = True
            return False  # stop listener

    # Hide the GUI while waiting for user input
    root.withdraw()
    print("Click anywhere to set position, or press Esc to cancel...")

    # Start mouse & keyboard listeners
    mouse_listener = mouse.Listener(on_click=on_click)
    key_listener = kb.Listener(on_press=on_key_press)
    mouse_listener.start()
    key_listener.start()

    # Wait until user clicks or presses Esc
    while mouse_listener.is_alive() and key_listener.is_alive():
        time.sleep(0.01)

    # Clean up listeners
    mouse_listener.stop()
    key_listener.stop()

    # Restore window
    root.deiconify()
    root.lift()
    root.focus_force()

    # Handle cancel
    if pos["cancel"]:
        print("❌ Pick canceled.")
        return

    # Update entries with picked coordinates
    if pos["x"] is not None and pos["y"] is not None:
        x_var.set(str(pos["x"]))
        y_var.set(str(pos["y"]))
        pos_var.set("pick")
        print(f"✅ Picked position: X={pos['x']}  Y={pos['y']}")

# --- "Pick" button ---
ttk.Button(frame_cursor, text="Pick", width=10, command=pick_position).grid(row=0, column=6, padx=5)

# ==== Buttons ====
frame_buttons = tk.Frame(root)
frame_buttons.pack(pady=10)

btn_start = ttk.Button(frame_buttons, text="Start (F6)", width=18, command=on_click_start)
btn_start.grid(row=0, column=0, padx=5, pady=5)

btn_stop = ttk.Button(frame_buttons, text="Stop (F6)", width=18, command=on_click_stop, state="disabled")
btn_stop.grid(row=0, column=1, padx=5, pady=5)

root.mainloop()
