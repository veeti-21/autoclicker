# autoclicker

Lightweight, configurable autoclicker written in Python.

A small tool to automate mouse clicks with configurable intervals, click type, number of clicks or duration, and optional hotkey control. Intended for productivity/testing tasks where repetitive clicking is required.

## Features
- Start/stop autoclicker with F6 hotkey
- Configurable click interval (hours, minutes, seconds, milliseconds)
- Click type: left / right / middle / button 4 / button 5 
- Keyboard hotkey support (single keys or key combinations)
- Option to run for a set number of clicks or until stopped
- Hold mode: press and release, or hold down continuously
- Position mode: current location or pick specific coordinates
- Save/load presets
- Auto-save last used settings
- Pin window option (always on top)

## Requirements
- Python 3.8+
- pip

### Required packages:
- pynput (for mouse/keyboard control)
- keyboard (for global hotkeys)
- tkinter (usually included with Python)

## Installation

Clone the repository:

```
git clone https://github.com/veeti-21/autoclicker.git
cd autoclicker
```

Install required packages (example):

```
pip install pynput keyboard
```

## Credits
Created by @veeti-21
