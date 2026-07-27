import customtkinter as ctk
from tkinter import ttk
from lib.database import get_db
from lib.tool_dialog import ToolDialog


class ToolDatabase(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.db = get_db()
        self.title("Werkzeugverwaltung")
        self.geometry("700x450")
        self.transient(master)
        self.grab_set()
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
        cols = ("name", "beschreibung", "preis", "einheit")
        heads = {"name": "Name", "beschreibung": "Beschreibung", "preis": "Preis", "einheit": "Einheit"}
        widths = {"name": 200, "beschreibung": 250, "preis": 80, "einheit": 80}
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=widths[c], minwidth=50)
        self.tree.bind("<Double-1>", lambda e: self._edit())
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        vsb.pack(side="right", fill="y", pady=5)
        vsb.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, x=0)

    def _load(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for t in self.db.tool_search(self.search_var.get()):
            price = f"{t['price']:.2f}".replace(".", ",")
            unit = "Std." if t.get("price_unit") == "h" else "Min."
            self.tree.insert("", "end", values=(
                t.get("name", ""), t.get("description", ""), f"{price}\u20ac", unit
            ), iid=str(t["id"]))

    def _get_selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _new(self):
        dlg = ToolDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _edit(self):
        tid = self._get_selected_id()
        if not tid:
            return
        dlg = ToolDialog(self, tid)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _delete(self):
        tid = self._get_selected_id()
        if not tid:
            return
        from tkinter import messagebox
        if messagebox.askyesno("Löschen", "Werkzeug wirklich löschen?"):
            self.db.tool_delete(tid)
            self._load()
