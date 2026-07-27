import customtkinter as ctk
from lib.database import get_db


class CustomerDialog(ctk.CTkToplevel):
    def __init__(self, master, customer_id=None):
        super().__init__(master)
        self.db = get_db()
        self.customer_id = customer_id
        self.title("Kunde bearbeiten" if customer_id else "Neuer Kunde")
        self.geometry("500x420")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result = None
        data = self.db.customer_get(customer_id) if customer_id else {}
        self._build_ui(data)

    def _build_ui(self, data):
        fields = [
            ("company", "Firma:"),
            ("first_name", "Vorname:"),
            ("last_name", "Nachname:"),
            ("street", "Straße:"),
            ("zip", "PLZ:"),
            ("city", "Ort:"),
            ("phone", "Telefon:"),
            ("email", "E-Mail:"),
            ("note", "Notiz:"),
        ]
        self.entries = {}
        for i, (key, label) in enumerate(fields):
            ctk.CTkLabel(self, text=label, width=80, anchor="w").grid(row=i, column=0, padx=(15, 5), pady=3, sticky="w")
            if key == "note":
                entry = ctk.CTkEntry(self, width=350)
            else:
                entry = ctk.CTkEntry(self, width=350)
            entry.insert(0, data.get(key, ""))
            entry.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            self.entries[key] = entry
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text="Speichern", command=self._save, width=120).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Abbrechen", command=self.destroy, width=120).pack(side="left", padx=10)

    def _save(self):
        data = {k: v.get() for k, v in self.entries.items()}
        if not data.get("company") and not data.get("last_name"):
            return
        data["id"] = self.customer_id
        self.result = self.db.customer_save(data)
        self.destroy()
