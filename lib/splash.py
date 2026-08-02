import tkinter as tk
import os
from PIL import Image, ImageTk

SPLASH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
SPLASH_FILE = os.path.join(SPLASH_DIR, "splashscreen.jpg")


def create_splash_window(master=None):
    win = tk.Toplevel(master)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    try:
        img = Image.open(SPLASH_FILE)
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        max_w = min(sw // 2, 600)
        max_h = min(sh // 2, 500)
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img, master=win)
        label = tk.Label(win, image=photo, border=0)
        label.image = photo
        label.pack()
        w, h = img.size
        x = (sw - w) // 2
        y = (sh - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.deiconify()
        win.lift()
        win.focus_force()
        win.update()
    except Exception as e:
        try:
            from lib.logger import get_logger
            get_logger().error(f"Splash-Fehler: {e}")
        except Exception:
            pass
        win.destroy()
        return None
    return win
