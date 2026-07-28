import customtkinter as ctk
from tkinter import ttk
from lib.database import get_db
from lib.material_dialog import MaterialDialog
from lib.icon import set_window_icon


class MaterialDatabase(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.db = get_db()
        self.title("Materialverwaltung")
        self.geometry("700x450")
        self.transient(master)
        self.grab_set()
        self.after(50, lambda: set_window_icon(self, self.master))
        self._build_ui()
        self._load()

    def _build_ui(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(top, text="Suchen:", font=("Segoe UI", 11)).pack(side="left", padx=(0, 5))
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._load())
        ctk.CTkEntry(top, textvariable=self.search_var, width=250, placeholder_text="Name...").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Neu", command=self._new, width=60).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Bearbeiten", command=self._edit, width=100).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Löschen", command=self._delete, width=80,
                       fg_color="#5c0000", hover_color="#8b0000").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Schließen", command=self.destroy, width=80).pack(side="right", padx=5)
        cols = ("name", "beschreibung", "preis")
        heads = {"name": "Name", "beschreibung": "Beschreibung", "preis": "Preis / m\u00b2"}
        widths = {"name": 200, "beschreibung": 300, "preis": 120}
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            align = "e" if c == "preis" else "w"
            self.tree.heading(c, text=heads[c], anchor=align)
            self.tree.column(c, width=widths[c], minwidth=50, anchor=align)
        self.tree.bind("<Double-1>", lambda e: self._edit())
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        vsb.pack(side="right", fill="y", pady=5)
        vsb.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, x=0)

    def _load(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for m in self.db.material_search(self.search_var.get()):
            price = f"{m['price_per_m2']:.2f}".replace(".", ",")
            self.tree.insert("", "end", values=(
                m.get("name", ""), m.get("description", ""), f"{price}\u20ac"
            ), iid=str(m["id"]))

    def _get_selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _new(self):
        dlg = MaterialDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _edit(self):
        mid = self._get_selected_id()
        if not mid:
            return
        dlg = MaterialDialog(self, mid)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _delete(self):
        mid = self._get_selected_id()
        if not mid:
            return
        from tkinter import messagebox
        if messagebox.askyesno("Löschen", "Material wirklich löschen?"):
            self.db.material_delete(mid)
            self._load()
