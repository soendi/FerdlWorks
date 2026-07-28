import customtkinter as ctk
from lib.database import get_db
from lib.icon import set_window_icon


class MaterialDialog(ctk.CTkToplevel):
    def __init__(self, master, material_id=None):
        super().__init__(master)
        self.db = get_db()
        self.material_id = material_id
        self.title("Material bearbeiten" if material_id else "Neues Material")
        self.geometry("500x280")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.after(50, lambda: set_window_icon(self, self.master))
        self.result = None
        data = self.db.material_get(material_id) if material_id else {}
        self._build_ui(data)

    def _build_ui(self, data):
        fields = [
            ("name", "Name:"),
            ("description", "Beschreibung:"),
            ("price_per_m2", "Preis pro m\xb2:"),
            ("note", "Notiz:"),
        ]
        self.entries = {}
        for i, (key, label) in enumerate(fields):
            ctk.CTkLabel(self, text=label, width=100, anchor="w").grid(row=i, column=0, padx=(15, 5), pady=5, sticky="w")
            if key == "price_per_m2":
                entry = ctk.CTkEntry(self, width=200)
                entry.insert(0, str(data.get(key, "0")).replace(".", ","))
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
                self.entries[key] = entry
            else:
                entry = ctk.CTkEntry(self, width=350)
                entry.insert(0, data.get(key, ""))
                entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
                self.entries[key] = entry
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text="Speichern", command=self._save, width=120).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Abbrechen", command=self.destroy, width=120).pack(side="left", padx=10)

    def _save(self):
        price_str = self.entries["price_per_m2"].get().replace(",", ".")
        try:
            price = float(price_str)
        except ValueError:
            price = 0
        data = {
            "name": self.entries["name"].get(),
            "description": self.entries["description"].get(),
            "price_per_m2": price,
            "note": self.entries["note"].get(),
            "id": self.material_id,
        }
        if not data["name"]:
            return
        self.result = self.db.material_save(data)
        self.destroy()
