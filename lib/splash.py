import tkinter as tk
import os
from PIL import Image, ImageTk

SPLASH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
SPLASH_FILE = os.path.join(SPLASH_DIR, "splashscreen.jpg")


class SplashForm(tk.Tk):
    def __init__(self, duration_ms=3000):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#2b2b2b")
        img = None
        if os.path.exists(SPLASH_FILE):
            try:
                pil_img = Image.open(SPLASH_FILE)
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                max_w = min(sw // 2, 600)
                max_h = min(sh // 2, 500)
                pil_img.thumbnail((max_w, max_h), Image.LANCZOS)
                img = ImageTk.PhotoImage(pil_img)
            except Exception:
                pass
        if img:
            lbl = tk.Label(self, image=img, border=0)
            lbl.image = img
            lbl.pack()
            w, h = pil_img.size
        else:
            w, h = 400, 200
            lbl = tk.Label(self, text="FerdlWorks", font=("Segoe UI", 24, "bold"),
                           fg="#8b0000", bg="#2b2b2b")
            lbl.pack(expand=True)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.after(duration_ms, self.destroy)


def show_splash(duration_ms=3000):
    splash = SplashForm(duration_ms=duration_ms)
    splash.mainloop()
    import tkinter as tk
    tk._default_root = None
