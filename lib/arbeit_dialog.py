import customtkinter as ctk
from lib.database import get_db
from lib.icon import set_window_icon


class ArbeitDialog(ctk.CTkToplevel):
    def __init__(self, master, arbeit_id=None):
        super().__init__(master)
        self.db = get_db()
        self.arbeit_id = arbeit_id
        self.title("Arbeit bearbeiten" if arbeit_id else "Neue Arbeit")
        self.geometry("500x320")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.after(50, lambda: set_window_icon(self, self.master))
        self.result = None
        data = self.db.arbeit_get(arbeit_id) if arbeit_id else {}
        self._build_ui(data)

    def _build_ui(self, data):
        fields = [
            ("name", "Name:"),
            ("description", "Beschreibung:"),
        ]
        self.entries = {}
        for i, (key, label) in enumerate(fields):
            ctk.CTkLabel(self, text=label, width=100, anchor="w").grid(row=i, column=0, padx=(15, 5), pady=5, sticky="w")
            entry = ctk.CTkEntry(self, width=350)
            entry.insert(0, data.get(key, ""))
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
            self.entries[key] = entry

        i = len(fields)
        ctk.CTkLabel(self, text="Preis:", width=100, anchor="w").grid(row=i, column=0, padx=(15, 5), pady=5, sticky="w")
        self.price_entry = ctk.CTkEntry(self, width=120)
        self.price_entry.insert(0, str(data.get("price", "0")).replace(".", ","))
        self.price_entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
        self.entries["price"] = self.price_entry

        self.price_unit_entry = ctk.CTkEntry(self, width=100)
        self.price_unit_entry.insert(0, data.get("price_unit", ""))
        self.price_unit_entry.grid(row=i, column=1, padx=(130, 5), pady=5, sticky="w")

        i += 1
        ctk.CTkLabel(self, text="Notiz:", width=100, anchor="w").grid(row=i, column=0, padx=(15, 5), pady=5, sticky="w")
        self.note_entry = ctk.CTkEntry(self, width=350)
        self.note_entry.insert(0, data.get("note", ""))
        self.note_entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
        self.entries["note"] = self.note_entry

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=i + 1, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text="Speichern", command=self._save, width=120).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Abbrechen", command=self.destroy, width=120).pack(side="left", padx=10)

    def _save(self):
        price_str = self.price_entry.get().replace(",", ".")
        try:
            price = float(price_str)
        except ValueError:
            price = 0
        data = {
            "name": self.entries["name"].get(),
            "description": self.entries["description"].get(),
            "price": price,
            "price_unit": self.price_unit_entry.get(),
            "note": self.entries["note"].get(),
            "id": self.arbeit_id,
        }
        if not data["name"]:
            return
        self.result = self.db.arbeit_save(data)
        self.destroy()