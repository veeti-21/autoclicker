import time
from pynput.keyboard import Key, Controller as KeyboardController

# Only available on Windows, same check as Autoclicker
try:
    import win32gui
    import win32con
    import win32process
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False


# Global variable to track last Spotify pause time for debounce
last_spotify_pause_time = 0

def pause_spotify():
    """
    Pause/play Spotify by sending a media_play_pause command.
    Tries to target Spotify-like applications directly to avoid pausing other media (e.g., YouTube).
    Includes a 500ms debounce to prevent double-triggering.
    """
    global last_spotify_pause_time
    current_time = time.time()
    
    # Debounce: ignore if called within 500ms of last call
    if current_time - last_spotify_pause_time < 0.5:
        return
        
    last_spotify_pause_time = current_time
    
    try:
        spotify_hwnd = None
        def find_spotify_window(hwnd, _):
            nonlocal spotify_hwnd
            # We are looking for a visible window with a title.
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
                    proc_name = win32process.GetModuleFileNameEx(handle, 0)
                    win32api.CloseHandle(handle)
                    if "spotify.exe" in proc_name.lower():
                        spotify_hwnd = hwnd
                        return False  # Stop enumeration
                except Exception:
                    pass # Could fail for some processes
            return True

        win32gui.EnumWindows(find_spotify_window, None)
  
        if spotify_hwnd:
            # Found spotify, send command to it
            WM_APPCOMMAND = 0x0319
            APPCOMMAND_MEDIA_PLAY_PAUSE = 14
            win32gui.PostMessage(spotify_hwnd, WM_APPCOMMAND, 0, APPCOMMAND_MEDIA_PLAY_PAUSE << 16)
        else:
            # If no specific window is found, fall back to the global key press.
            raise Exception("Spotify process not found.")
         
    except Exception as e:
        print(f"Failed to send targeted media command: {e}")
        