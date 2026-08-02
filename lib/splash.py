import tkinter as tk
import os
from PIL import Image, ImageTk

SPLASH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
SPLASH_FILE = os.path.join(SPLASH_DIR, "splashscreen.jpg")


def show_splash(master=None):
    splash_win = tk.Toplevel(master)
    splash_win.overrideredirect(True)
    try:
        img = Image.open(SPLASH_FILE)
        sw = splash_win.winfo_screenwidth()
        sh = splash_win.winfo_screenheight()
        max_w = min(sw // 2, 600)
        max_h = min(sh // 2, 500)
        img.thumbnail((max_w, max_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        label = tk.Label(splash_win, image=photo, border=0)
        label.image = photo
        label.pack()
        w, h = img.size
        x = (sw - w) // 2
        y = (sh - h) // 2
        splash_win.geometry(f"{w}x{h}+{x}+{y}")
        splash_win.lift()
        splash_win.attributes("-topmost", True)
    except Exception:
        splash_win.destroy()
        return None
    return splash_win
