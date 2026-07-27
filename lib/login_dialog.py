import customtkinter as ctk
from lib.database import get_db
from lib.password import check_password, is_master_password, hash_password


class LoginDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.db = get_db()
        self.title("Anmeldung - FerdlWorks")
        self.geometry("400x250")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._authenticated = False
        self._master_mode = False
        self._build_ui()
        self.center_on_screen()
        self.grab_set()

    def center_on_screen(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = 400
        h = 250
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        ctk.CTkLabel(self, text="FerdlWorks", font=("Segoe UI", 20, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(pady=(30, 10))
        ctk.CTkLabel(self, text="Bitte Passwort eingeben:", font=("Segoe UI", 11)).pack()
        self.pw_entry = ctk.CTkEntry(self, width=250, show="*", placeholder_text="Passwort")
        self.pw_entry.pack(pady=10)
        self.pw_entry.bind("<Return>", lambda e: self._login())
        self.error_label = ctk.CTkLabel(self, text="", font=("Segoe UI", 10),
                                        text_color=("#b22222", "#b22222"))
        self.error_label.pack()
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Anmelden", command=self._login, width=120).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Beenden", command=self._on_close, width=120).pack(side="left", padx=10)
        self.pw_entry.focus_set()

    def _login(self):
        settings = self.db.settings_get_all()
        stored_hash = settings.get("user_password", "")
        input_pw = self.pw_entry.get()
        if not input_pw:
            self.error_label.configure(text="Bitte Passwort eingeben.")
            return
        if is_master_password(input_pw):
            self._authenticated = True
            self._master_mode = True
            self.destroy()
            return
        if stored_hash:
            if check_password(input_pw, stored_hash):
                self._authenticated = True
                self._master_mode = False
                self.destroy()
                return
            else:
                self.error_label.configure(text="Falsches Passwort!")
                self.pw_entry.delete(0, "end")
                self.pw_entry.focus_set()
                return
        self._authenticated = True
        self._master_mode = False
        self.destroy()

    def _on_close(self):
        self._authenticated = False
        self.destroy()

    def is_authenticated(self):
        return self._authenticated

    def is_master_mode(self):
        return self._master_mode
