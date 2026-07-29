import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from lib.database import get_db
from lib.arbeit_dialog import ArbeitDialog
from lib.icon import set_window_icon


class ArbeitDatabase(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.db = get_db()
        self.title("Arbeitenverwaltung")
        self.geometry("800x500")
        self.minsize(600, 400)
        self.transient(master)
        self.grab_set()
        self.after(50, lambda: set_window_icon(self, self.master))
        self._build_ui()
        self._load()

    def _build_ui(self):
        # Toolbar
        tb = ctk.CTkFrame(self, fg_color="transparent")
        tb.pack(fill="x", padx=10, pady=10)
        ctk.CTkButton(tb, text="Neu", command=self._new, width=80).pack(side="left", padx=5)
        ctk.CTkButton(tb, text="Bearbeiten", command=self._edit, width=80).pack(side="left", padx=5)
        ctk.CTkButton(tb, text="Löschen", command=self._delete, width=80,
                      fg_color="#8b0000", hover_color="#5c0000").pack(side="left", padx=5)

        # Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Arbeit.Treeview", background="#2a2a2a", foreground="#e0e0e0",
                        fieldbackground="#2a2a2a", rowheight=26, font=("Segoe UI", 12))
        style.map("Arbeit.Treeview", background=[("selected", "#8b0000")], foreground=[("selected", "#ffffff")])
        style.configure("Arbeit.Treeview.Heading", font=("Segoe UI", 11, "bold"))
        style.layout("Arbeit.Treeview", [("Arbeit.Treeview.treearea", {"sticky": "nswe"})])

        cols = ("name", "description", "price", "unit")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", style="Arbeit.Treeview", selectmode="browse")
        self.tree.heading("name", text="Name", anchor="w")
        self.tree.heading("description", text="Beschreibung", anchor="w")
        self.tree.heading("price", text="Preis", anchor="e")
        self.tree.heading("unit", text="Einheit", anchor="center")
        self.tree.column("name", width=200, anchor="w", minwidth=120)
        self.tree.column("description", width=350, anchor="w", minwidth=150)
        self.tree.column("price", width=80, anchor="e", minwidth=60)
        self.tree.column("unit", width=80, anchor="center", minwidth=60)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 10), pady=(0, 10))

        self.tree.bind("<Double-1>", lambda e: self._edit())

    def _load(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for a in self.db.arbeit_search(""):
            price_str = f"{a.get('price', 0):.2f}".replace(".", ",")
            self.tree.insert("", "end", iid=str(a["id"]), values=(
                a.get("name", ""),
                a.get("description", ""),
                price_str,
                a.get("price_unit", "")
            ))

    def _new(self):
        dlg = ArbeitDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _edit(self):
        sel = self.tree.selection()
        if not sel:
            return
        aid = int(sel[0])
        dlg = ArbeitDialog(self, aid)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _delete(self):
        sel = self.tree.selection()
        if not sel:
            return
        aid = int(sel[0])
        name = self.tree.item(aid, "values")[0]
        if messagebox.askyesno("Löschen", f"Arbeit '{name}' wirklich löschen?"):
            self.db.arbeit_delete(aid)
            self._load()