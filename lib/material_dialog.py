import customtkinter as ctk
from lib.database import get_db
from lib.icon import set_window_icon


class MaterialDialog(ctk.CTkToplevel):
    def __init__(self, master, material_id=None):
        super().__init__(master)
        self.db = get_db()
        self.material_id = material_id
        self.title("Material bearbeiten" if material_id else "Neues Material")
        self.geometry("500x360")
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
        self.price_entry.insert(0, str(data.get("price_per_m2", "0")).replace(".", ","))
        self.price_entry.grid(row=i, column=1, padx=5, pady=5, sticky="w")
        self.entries["price_per_m2"] = self.price_entry

        units = ["m\u00b2", "Stk", "Krt", "kg", "g", "l", "m", "Stg", "Rolle", "Paket", "Set", "Paar"]
        current_unit = data.get("price_unit", "m\u00b2")
        if current_unit not in units:
            units.insert(0, current_unit)
        self.price_unit_var = ctk.StringVar(value=current_unit)
        ctk.CTkOptionMenu(self, variable=self.price_unit_var, values=units, width=100).grid(row=i, column=1, padx=(130, 5), pady=5, sticky="w")

        i += 1
        ctk.CTkLabel(self, text="Gr\u00f6\u00dfe (cm):", width=100, anchor="w").grid(row=i, column=0, padx=(15, 5), pady=5, sticky="w")
        size_frame = ctk.CTkFrame(self, fg_color="transparent")
        size_frame.grid(row=i, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(size_frame, text="L:", font=("Segoe UI", 12)).pack(side="left")
        self.length_entry = ctk.CTkEntry(size_frame, width=80)
        self.length_entry.insert(0, self._fmt_num(data.get("length", 0)))
        self.length_entry.pack(side="left", padx=2)
        ctk.CTkLabel(size_frame, text="B:", font=("Segoe UI", 12)).pack(side="left", padx=(8, 0))
        self.width_entry = ctk.CTkEntry(size_frame, width=80)
        self.width_entry.insert(0, self._fmt_num(data.get("width", 0)))
        self.width_entry.pack(side="left", padx=2)
        self.entries["length"] = self.length_entry
        self.entries["width"] = self.width_entry

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
            "price_per_m2": price,
            "price_unit": self.price_unit_var.get(),
            "length": self._parse_num(self.entries["length"].get()),
            "width": self._parse_num(self.entries["width"].get()),
            "note": self.entries["note"].get(),
            "id": self.material_id,
        }
        if not data["name"]:
            return
        self.result = self.db.material_save(data)
        self.destroy()

    @staticmethod
    def _fmt_num(value):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return ""
        if v <= 0:
            return ""
        if v == int(v):
            return str(int(v))
        return f"{v:g}".replace(".", ",")

    @staticmethod
    def _parse_num(value):
        try:
            return float(str(value).strip().replace(",", "."))
        except ValueError:
            return 0
