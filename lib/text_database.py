import customtkinter as ctk
from tkinter import ttk, messagebox
from lib.database import get_db
from lib.icon import set_window_icon


class TextDatabase(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.db = get_db()
        self.title("Textverwaltung")
        self.geometry("700x500")
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
        ctk.CTkEntry(top, textvariable=self.search_var, width=250,
                      placeholder_text="Textname...").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Neu", command=self._new, width=60).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Bearbeiten", command=self._edit, width=100).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Löschen", command=self._delete, width=80,
                       fg_color="#5c0000", hover_color="#8b0000").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Schließen", command=self.destroy, width=80).pack(side="right", padx=5)

        cols = ("name", "content")
        heads = {"name": "Name", "content": "Text"}
        self.tree = ttk.Treeview(self, columns=cols, show="headings", selectmode="browse", height=8)
        for c in cols:
            self.tree.heading(c, text=heads[c])
            self.tree.column(c, width=200, minwidth=80)
        self.tree.column("name", width=200)
        self.tree.column("content", width=450)
        self.tree.bind("<Double-1>", lambda e: self._edit())
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        vsb.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, x=0)

    def _load(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for t in self.db.text_search(self.search_var.get()):
            content = t.get("content", "")
            preview = content[:80] + "..." if len(content) > 80 else content
            self.tree.insert("", "end", values=(t["name"], preview), iid=str(t["id"]))

    def _get_selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _new(self):
        dlg = TextDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _edit(self):
        tid = self._get_selected_id()
        if not tid:
            messagebox.showinfo("Hinweis", "Kein Text ausgewählt.")
            return
        dlg = TextDialog(self, text_id=tid)
        self.wait_window(dlg)
        if dlg.result:
            self._load()

    def _delete(self):
        tid = self._get_selected_id()
        if not tid:
            messagebox.showinfo("Hinweis", "Kein Text ausgewählt.")
            return
        if messagebox.askyesno("Löschen", "Diesen Text wirklich löschen?"):
            self.db.text_delete(tid)
            self._load()


class TextDialog(ctk.CTkToplevel):
    def __init__(self, master, text_id=None):
        super().__init__(master)
        self.db = get_db()
        self.text_id = text_id
        self.title("Text bearbeiten" if text_id else "Neuer Text")
        self.geometry("500x350")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.result = None
        data = self.db.text_get(text_id) if text_id else {}
        self._build_ui(data)

    def _build_ui(self, data):
        ctk.CTkLabel(self, text="Name:", width=60, anchor="w").grid(row=0, column=0, padx=(15, 5), pady=10, sticky="w")
        self.name_entry = ctk.CTkEntry(self, width=380)
        self.name_entry.insert(0, data.get("name", ""))
        self.name_entry.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        ctk.CTkLabel(self, text="Text:", width=60, anchor="w").grid(row=1, column=0, padx=(15, 5), pady=5, sticky="nw")
        self.content_text = ctk.CTkTextbox(self, width=380, height=180)
        self.content_text.insert("1.0", data.get("content", ""))
        self.content_text.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15)
        ctk.CTkButton(btn_frame, text="Speichern", command=self._save, width=120).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Abbrechen", command=self.destroy, width=120).pack(side="left", padx=10)

    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("Fehler", "Bitte geben Sie einen Namen ein.")
            return
        data = {"name": name, "content": self.content_text.get("1.0", "end-1c")}
        data["id"] = self.text_id
        self.result = self.db.text_save(data)
        self.destroy()
