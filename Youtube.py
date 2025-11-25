import time
from pynput.keyboard import Key, Controller as KeyboardController

try:
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Global variable to track last YouTube pause time for debounce
last_youtube_pause_time = 0

def pause_youtube():
    """
    Pause/play YouTube video by bringing the browser to foreground and sending Spacebar.
    This is the most reliable method for browser control, though it steals focus.
    Includes a 500ms debounce to prevent double-triggering.
    """
    global last_youtube_pause_time
    current_time = time.time()
    
    # Debounce: ignore if called within 500ms of last call
    if current_time - last_youtube_pause_time < 0.5:
        return
        
    last_youtube_pause_time = current_time

    try:
        # Try to find browser window if Windows API is available
        if HAS_WIN32:
            found_browser = False
            def enum_handler(hwnd, _):
                nonlocal found_browser
                if found_browser:
                    return False # Stop if already found
                    
                window_title = win32gui.GetWindowText(hwnd)
                title_lower = window_title.lower()
                
                # Only target windows with "youtube" in the title to avoid interference
                if win32gui.IsWindowVisible(hwnd) and "youtube" in title_lower:
                    try:
                        # Bring window to foreground
                        # Only restore if minimized (IsIconic) to avoid exiting full screen
                        if win32gui.IsIconic(hwnd):
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        
                        win32gui.SetForegroundWindow(hwnd)
                        
                        # Small delay to ensure focus switch happens
                        time.sleep(0.05)
                        
                        # Send Spacebar
                        kb_controller = KeyboardController()
                        kb_controller.press(Key.space)
                        kb_controller.release(Key.space)
                        
                        found_browser = True
                        return False
                    except Exception:
                        # Sometimes SetForegroundWindow fails, but we proceed or pass.
                        pass
                return True
            
            win32gui.EnumWindows(enum_handler, None)
            
            if found_browser:
                return

        # Fallback: Do nothing if no specific window is found.
        # We explicitly DO NOT send a global media key here to avoid Spotify interference.
                
    except Exception as e:
        print(f"Failed to pause YouTube: {e}")