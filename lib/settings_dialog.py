import customtkinter as ctk
from lib.database import get_db
from lib.registry import reg_read, reg_write
from lib.autostart import autostart_enable, autostart_disable, autostart_is_enabled
from lib.password import hash_password, check_password, is_master_password


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, master_mode=False):
        super().__init__(master)
        self.db = get_db()
        self.master_mode = master_mode
        self.title("Einstellungen")
        self.geometry("650x580")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.settings = self.db.settings_get_all()
        self._build_ui()

    def _build_ui(self):
        tabview = ctk.CTkTabview(self, width=620, height=480)
        tabview.pack(padx=15, pady=15, fill="both", expand=True)

        # --- Absender ---
        tab1 = tabview.add("Absender")
        entries = {}
        fields = [
            ("company", "Firma:"),
            ("first_name", "Vorname:"),
            ("last_name", "Nachname:"),
            ("street", "Straße:"),
            ("zip", "PLZ:"),
            ("city", "Ort:"),
            ("phone", "Telefon:"),
            ("email", "E-Mail:"),
            ("tax_id", "Steuernummer:"),
        ]
        for i, (key, label) in enumerate(fields):
            ctk.CTkLabel(tab1, text=label, width=100, anchor="w").grid(row=i, column=0, padx=(10, 5), pady=3, sticky="w")
            entry = ctk.CTkEntry(tab1, width=350)
            entry.insert(0, self.settings.get(f"sender_{key}", ""))
            entry.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            entries[key] = entry
        self._sender_entries = entries

        # --- Rechnung ---
        tab2 = tabview.add("Rechnung")
        ctk.CTkLabel(tab2, text="Mehrwertsteuer-Satz (%):", width=150, anchor="w").grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")
        self.tax_entry = ctk.CTkEntry(tab2, width=100)
        self.tax_entry.insert(0, self.settings.get("tax_rate", "19"))
        self.tax_entry.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        ctk.CTkLabel(tab2, text="Standard Rabatt (%):", width=150, anchor="w").grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.discount_entry = ctk.CTkEntry(tab2, width=100)
        self.discount_entry.insert(0, self.settings.get("default_discount", "0"))
        self.discount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # --- SMTP ---
        tab3 = tabview.add("E-Mail (SMTP)")
        smtp_fields = [
            ("smtp_host", "SMTP-Server:"),
            ("smtp_port", "Port:"),
            ("smtp_user", "Benutzername:"),
            ("smtp_pass", "Passwort:"),
            ("smtp_sender", "Absender-E-Mail:"),
            ("smtp_encryption", "Verschlüsselung:"),
        ]
        self._smtp_entries = {}
        for i, (key, label) in enumerate(smtp_fields):
            ctk.CTkLabel(tab3, text=label, width=120, anchor="w").grid(row=i, column=0, padx=(10, 5), pady=3, sticky="w")
            if key == "smtp_encryption":
                opt = ctk.CTkOptionMenu(tab3, values=["SSL/TLS", "STARTTLS", "Keine"], width=200)
                val = self.settings.get(key, "SSL/TLS")
                opt.set(val if val in ["SSL/TLS", "STARTTLS", "Keine"] else "SSL/TLS")
                opt.grid(row=i, column=1, padx=5, pady=3, sticky="w")
                self._smtp_entries[key] = opt
            elif key == "smtp_port":
                entry = ctk.CTkEntry(tab3, width=80)
                entry.insert(0, self.settings.get(key, "465"))
                entry.grid(row=i, column=1, padx=5, pady=3, sticky="w")
                self._smtp_entries[key] = entry
            elif key == "smtp_pass":
                entry = ctk.CTkEntry(tab3, width=300, show="*")
                entry.insert(0, self.settings.get(key, ""))
                entry.grid(row=i, column=1, padx=5, pady=3, sticky="w")
                self._smtp_entries[key] = entry
            else:
                entry = ctk.CTkEntry(tab3, width=300)
                entry.insert(0, self.settings.get(key, ""))
                entry.grid(row=i, column=1, padx=5, pady=3, sticky="w")
                self._smtp_entries[key] = entry

        # --- Drucker ---
        tab4 = tabview.add("Drucker")
        self._printer_var = ctk.StringVar(value=self.settings.get("printer_name", ""))
        ctk.CTkLabel(tab4, text="Standard-Drucker:", anchor="w").grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")
        self.printer_menu = ctk.CTkOptionMenu(tab4, values=self._get_printers(), variable=self._printer_var, width=300)
        self.printer_menu.grid(row=0, column=1, padx=5, pady=10, sticky="w")
        ctk.CTkLabel(tab4, text="(Leer lassen für Systemstandard)", font=("Segoe UI", 10),
                     text_color="#888888").grid(row=1, column=1, padx=5, pady=0, sticky="w")

        # --- Allgemein ---
        tab5 = tabview.add("Allgemein")
        self.autostart_var = ctk.BooleanVar(value=autostart_is_enabled())
        ctk.CTkCheckBox(tab5, text="Autostart (mit Windows starten)", variable=self.autostart_var,
                        font=("Segoe UI", 11)).grid(row=0, column=0, columnspan=2, padx=15, pady=10, sticky="w")
        ctk.CTkLabel(tab5, text="Passwort-Schutz:", font=("Segoe UI", 11, "bold"),
                     text_color=("#8b0000", "#8b0000")).grid(row=1, column=0, columnspan=2, padx=15, pady=(15, 5), sticky="w")
        stored_hash = self.settings.get("user_password", "")
        has_password = bool(stored_hash)
        ctk.CTkLabel(tab5, text="Aktuelles Passwort:", anchor="w").grid(row=2, column=0, padx=15, pady=3, sticky="w")
        self.old_pw = ctk.CTkEntry(tab5, width=250, show="*")
        self.old_pw.grid(row=2, column=1, padx=5, pady=3, sticky="w")
        self.old_pw.bind("<KeyRelease>", lambda e: self._check_pw_access())
        ctk.CTkLabel(tab5, text="Neues Passwort:", anchor="w").grid(row=3, column=0, padx=15, pady=3, sticky="w")
        self.new_pw = ctk.CTkEntry(tab5, width=250, show="*")
        self.new_pw.grid(row=3, column=1, padx=5, pady=3, sticky="w")
        self._pw_unlocked = False
        self._pw_unlock_label = ctk.CTkLabel(tab5, text="", font=("Segoe UI", 10, "bold"),
                                              text_color=("#8b0000", "#8b0000"))
        self._pw_unlock_label.grid(row=4, column=0, columnspan=2, padx=15, pady=2, sticky="w")

        ctk.CTkLabel(tab5, text="(Leer lassen = Passwort löschen)", font=("Segoe UI", 9),
                     text_color="#666666").grid(row=5, column=1, padx=5, pady=0, sticky="w")

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 15))
        ctk.CTkButton(btn_frame, text="Speichern", command=self._save, width=120).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Abbrechen", command=self.destroy, width=120).pack(side="left", padx=10)

    def _check_pw_access(self):
        stored_hash = self.settings.get("user_password", "")
        old_pw = self.old_pw.get()
        if self.master_mode:
            self._pw_unlock_label.configure(text="(Master-Modus aktiv – Passwortänderung erlaubt)")
            self.new_pw.configure(state="normal")
            return
        if not stored_hash:
            self._pw_unlock_label.configure(text="(Kein Passwort gesetzt – Neues Passwort eingeben)")
            self.new_pw.configure(state="normal")
            return
        if old_pw and (check_password(old_pw, stored_hash) or is_master_password(old_pw)):
            self._pw_unlock_label.configure(text="Passwort bestätigt – Änderung erlaubt.")
            self.new_pw.configure(state="normal")
        else:
            self._pw_unlock_label.configure(text="")
            self.new_pw.configure(state="disabled")

    def _get_printers(self):
        try:
            import win32print
            printers = [p[2] for p in win32print.EnumPrinters(2)]
            return printers if printers else ["Keine Drucker gefunden"]
        except Exception:
            return ["Druckererkennung nicht verfügbar"]

    def _save(self):
        data = {}
        for key, entry in self._sender_entries.items():
            data[f"sender_{key}"] = entry.get()
        try:
            data["tax_rate"] = self.tax_entry.get().replace(",", ".")
            float(data["tax_rate"])
        except ValueError:
            data["tax_rate"] = "19"
        try:
            data["default_discount"] = self.discount_entry.get().replace(",", ".")
            float(data["default_discount"])
        except ValueError:
            data["default_discount"] = "0"
        for key, entry in self._smtp_entries.items():
            data[key] = entry.get()
        data["printer_name"] = self._printer_var.get()
        old_pw = self.old_pw.get()
        new_pw = self.new_pw.get()
        stored_hash = self.settings.get("user_password", "")
        pw_unlocked = False
        if stored_hash:
            if old_pw and (check_password(old_pw, stored_hash) or is_master_password(old_pw)):
                pw_unlocked = True
            elif self.master_mode:
                pw_unlocked = True
        else:
            pw_unlocked = True
        if pw_unlocked:
            if new_pw:
                data["user_password"] = hash_password(new_pw)
            else:
                data["user_password"] = ""
        self.db.settings_set_multi(data)
        if self.autostart_var.get():
            autostart_enable()
        else:
            autostart_disable()
        self.destroy()
