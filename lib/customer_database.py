import customtkinter as ctk
from tkinter import ttk
from lib.database import get_db
from lib.customer_dialog import CustomerDialog


class CustomerDatabase(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.db = get_db()
        self.title("Kundenkartei")
        self.geometry("800x500")
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
        ctk.CTkEntry(top, textvariable=self.search_var, width=250, placeholder_text="Name, Ort...").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Neu", command=self._new, width=60).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Bearbeiten", command=self._edit, width=100).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Löschen", command=self._delete, width=80,
                       fg_color="#5c0000", hover_color="#8b0000").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Schließen", command=self.destroy, width=80).pack(side="right", padx=5)
        cols = ("firma", "vorname", "nachname", "plz", "ort", "telefon", "email")
        heads = {"firma": "Firma", "vorname": "Vorname", "nachname": "Nachname",
                 "plz": "PLZ", "ort": "Ort", "telefon": "Telefon", "email": "E-Mail"}
        widths = {"firma": 180, "vorname": 100, "nachname": 120, "plz": 60, "ort": 120, "telefon": 120, "email": 180}
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
        for c in self.db.customer_search(self.search_var.get()):
            self.tree.insert("", "end", values=(
                c.get("company", ""), c.get("first_name", ""), c.get("last_name", ""),
                c.get("zip", ""), c.get("city", ""), c.get("phone", ""), c.get("email", "")
            ), iid=str(c["id"]))

    def _get_selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _new(self):
        dlg = CustomerDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _edit(self):
        cid = self._get_selected_id()
        if not cid:
            return
        dlg = CustomerDialog(self, cid)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _delete(self):
        cid = self._get_selected_id()
        if not cid:
            return
        from tkinter import messagebox
        if messagebox.askyesno("Löschen", "Kunden wirklich löschen?"):
            self.db.customer_delete(cid)
            self._load()
