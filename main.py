import sys
import os
import subprocess
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image
from datetime import datetime

from lib.logger import setup_logger, get_logger, get_log_path
from lib.registry import reg_write, reg_read, reg_delete_all
from lib.icon import create_icon
from lib.database import get_db, DB_PATH
from lib.settings_dialog import SettingsDialog
from lib.customer_dialog import CustomerDialog
from lib.customer_database import CustomerDatabase
from lib.tool_database import ToolDatabase
from lib.material_database import MaterialDatabase
from lib.pdf_gen import generate_pdf
from lib.email_sender import send_email
from lib.updater import check_for_update, download_installer, install_update
from lib.autostart import autostart_enable, autostart_disable, autostart_is_enabled
from lib.cloud_backup import gdrive_backup, gdrive_authorize, onedrive_backup, onedrive_authorize
from version import VERSION, APP_NAME, COMPANY_NAME

THEME_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ferdlworks_theme.json")


class PositionItem:
    def __init__(self, pos_type, ref_id, description, quantity, unit, price_per_unit, total, extra_data=None):
        self.pos_type = pos_type
        self.ref_id = ref_id
        self.description = description
        self.quantity = quantity
        self.unit = unit
        self.price_per_unit = price_per_unit
        self.total = total
        self.extra_data = extra_data or {}


class FerdlWorksApp(ctk.CTk):
    def __init__(self, master_mode=False):
        super().__init__()
        self.logger = get_logger()
        self.db = get_db()
        self._master_mode = master_mode
        self.title(f"{APP_NAME} v{VERSION}")
        icon_path = create_icon()
        try:
            self.iconbitmap(icon_path)
        except Exception:
            pass
        self.minsize(800, 620)
        self.geometry("1024x720")
        self._current_doc_id = None
        self._positions = []
        self._build_menu()
        self._build_ui()
        self.logger.info(f"{APP_NAME} v{VERSION} gestartet (Master-Mode: {master_mode})")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ===================== STANDARD-MENÜ =====================
    def _build_menu(self):
        mb = tk.Menu(self, font=("Segoe UI", 10))
        datei = tk.Menu(mb, tearoff=False, font=("Segoe UI", 10))
        datei.add_command(label="Kundenkartei...", command=self._open_customer_mgmt, accelerator="Strg+K")
        datei.add_separator()
        datei.add_command(label="Beenden", command=self._on_close, accelerator="Strg+Q")
        mb.add_cascade(label="Datei", menu=datei)

        wkz = tk.Menu(mb, tearoff=False, font=("Segoe UI", 10))
        wkz.add_command(label="Werkzeuge verwalten...", command=self._open_tool_mgmt)
        wkz.add_command(label="Material verwalten...", command=self._open_material_mgmt)
        mb.add_cascade(label="Werkzeuge & Material", menu=wkz)

        einst = tk.Menu(mb, tearoff=False, font=("Segoe UI", 10))
        einst.add_command(label="Einstellungen...", command=self._open_settings, accelerator="Strg+E")
        einst.add_separator()
        einst.add_command(label="Datensicherung erstellen...", command=self._backup_data)
        einst.add_command(label="Datensicherung wiederherstellen...", command=self._restore_data)
        einst.add_separator()
        einst.add_command(label="Google Drive Backup...", command=self._cloud_gdrive)
        einst.add_command(label="OneDrive Backup...", command=self._cloud_onedrive)
        mb.add_cascade(label="Einstellungen", menu=einst)

        hilfe = tk.Menu(mb, tearoff=False, font=("Segoe UI", 10))
        hilfe.add_command(label="Auf Updates prüfen...", command=self._check_update, accelerator="Strg+U")
        hilfe.add_separator()
        hilfe.add_command(label="Logdatei öffnen", command=self._open_log)
        hilfe.add_separator()
        hilfe.add_command(label="Info...", command=self._show_info)
        hilfe.add_separator()
        hilfe.add_command(label="Deinstallieren...", command=self._uninstall)
        mb.add_cascade(label="Hilfe", menu=hilfe)
        self.configure(menu=mb)

        # Tastaturkürzel
        self.bind_all("<Control-k>", lambda e: self._open_customer_mgmt())
        self.bind_all("<Control-q>", lambda e: self._on_close())
        self.bind_all("<Control-e>", lambda e: self._open_settings())
        self.bind_all("<Control-u>", lambda e: self._check_update())

    # ===================== UI =====================
    def _build_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Kunde ---
        cust = ctk.CTkFrame(main, corner_radius=6)
        cust.pack(fill="x", padx=8, pady=(4, 2))
        ctk.CTkLabel(cust, text="Kunde:", font=("Segoe UI", 12, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(side="left", padx=(10, 5))
        self.cust_var = ctk.StringVar()
        self.cust_var.trace_add("write", lambda *a: self._filter_customers())
        self.cust_entry = ctk.CTkEntry(cust, width=220, placeholder_text="Namen eingeben...",
                                       textvariable=self.cust_var)
        self.cust_entry.pack(side="left", padx=5)
        self.cust_listbox = tk.Listbox(cust, height=5, width=40,
                                       font=("Segoe UI", 10), exportselection=False)
        self.cust_listbox.pack(side="left", padx=2, fill="y")
        self.cust_listbox.bind("<<ListboxSelect>>", lambda e: self._pick_customer())
        self._cust_data = []
        ctk.CTkButton(cust, text="Neu", width=50, command=self._new_customer,
                       fg_color="#5c0000", hover_color="#8b0000").pack(side="left", padx=2)
        ctk.CTkButton(cust, text="Bearbeiten", width=80, command=self._edit_customer,
                       fg_color="#5c0000", hover_color="#8b0000").pack(side="left", padx=2)
        self._customer_id = None
        # Dokument-Typ
        dtype_f = ctk.CTkFrame(cust, fg_color="transparent")
        dtype_f.pack(side="right", padx=10)
        self.doc_type_var = ctk.StringVar(value="RG")
        ctk.CTkRadioButton(dtype_f, text="Rechnung", variable=self.doc_type_var, value="RG",
                           font=("Segoe UI", 11)).pack(side="left", padx=5)
        ctk.CTkRadioButton(dtype_f, text="Lieferschein", variable=self.doc_type_var, value="LS",
                           font=("Segoe UI", 11)).pack(side="left", padx=5)

        # --- Positionen (Tabelle) ---
        pos_frame = ctk.CTkFrame(main, corner_radius=6)
        pos_frame.pack(fill="both", expand=True, padx=8, pady=2)
        ctk.CTkLabel(pos_frame, text="Positionen", font=("Segoe UI", 11, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(anchor="w", padx=10, pady=(6, 2))
        cols = ("pos", "beschreibung", "menge", "einheit", "ep", "gesamt")
        heads = {"pos": "Pos.", "beschreibung": "Beschreibung", "menge": "Menge",
                 "einheit": "Einheit", "ep": "EP", "gesamt": "Gesamt"}
        widths = {"pos": 40, "beschreibung": 300, "menge": 60, "einheit": 60, "ep": 80, "gesamt": 90}
        self.pos_tree = ttk.Treeview(pos_frame, columns=cols, show="headings", height=5)
        for c in cols:
            self.pos_tree.heading(c, text=heads[c])
            self.pos_tree.column(c, width=widths[c], minwidth=30, anchor="w" if c in ("pos", "beschreibung") else "e")
        self.pos_tree.bind("<Delete>", lambda e: self._remove_selected_position())
        vsb = ttk.Scrollbar(pos_frame, orient="vertical", command=self.pos_tree.yview)
        self.pos_tree.configure(yscrollcommand=vsb.set)
        self.pos_tree.pack(fill="both", expand=True, padx=10, pady=2)
        vsb.pack(side="right", fill="y")
        vsb.place(in_=self.pos_tree, relx=1.0, rely=0, relheight=1.0, x=0)

        # --- Artikel-Suche (kombiniert: Werkzeug + Material) ---
        search_frame = ctk.CTkFrame(main, corner_radius=6)
        search_frame.pack(fill="x", padx=8, pady=2)
        self._build_search_panel(search_frame)

        # --- Detail-Panel (kontextabhängig) ---
        self.detail_frame = ctk.CTkFrame(main, corner_radius=6, height=60)
        self.detail_frame.pack(fill="x", padx=8, pady=2)
        self._build_detail_panel(self.detail_frame)
        self._hide_detail()

        # --- Footer ---
        footer = ctk.CTkFrame(main, corner_radius=6)
        footer.pack(fill="x", padx=8, pady=4)
        self._build_footer(footer)

    # ===================== KUNDENSUCHE =====================
    def _filter_customers(self):
        query = self.cust_var.get()
        self._cust_data = self.db.customer_search(query)
        self.cust_listbox.delete(0, "end")
        for c in self._cust_data:
            name = c.get("company") or f"{c.get('last_name', '')} {c.get('first_name', '')}".strip()
            orts = c.get("city", "")
            self.cust_listbox.insert("end", f"{name}  ({orts})" if orts else name)

    def _pick_customer(self):
        sel = self.cust_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._cust_data):
            self._customer_id = self._cust_data[idx]["id"]
            self.cust_var.set(self.cust_listbox.get(idx))

    def _get_selected_customer_id(self):
        return self._customer_id

    def _new_customer(self):
        dlg = CustomerDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._filter_customers()

    def _edit_customer(self):
        if not self._customer_id:
            return
        dlg = CustomerDialog(self, self._customer_id)
        self.wait_window(dlg)
        if dlg.result:
            self._filter_customers()

    # ===================== ARTIKEL-SUCHE =====================
    def _build_search_panel(self, parent):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(row, text="Artikel suchen:", font=("Segoe UI", 11, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(side="left", padx=(0, 8))
        self.art_var = ctk.StringVar()
        self.art_var.trace_add("write", lambda *a: self._search_articles())
        ctk.CTkEntry(row, textvariable=self.art_var, width=280,
                      placeholder_text="Werkzeug oder Material...").pack(side="left", padx=5)

        # Ergebnisliste (2 Spalten)
        result_frame = ctk.CTkFrame(parent, fg_color="transparent")
        result_frame.pack(fill="x", padx=10, pady=(2, 6))
        self.art_listbox = tk.Listbox(result_frame, height=4, font=("Segoe UI", 10),
                                       exportselection=False)
        self.art_listbox.pack(side="left", fill="x", expand=True)
        self.art_listbox.bind("<<ListboxSelect>>", lambda e: self._select_article())
        self._art_results = []

    def _search_articles(self):
        query = self.art_var.get()
        self._art_results = self.db.combined_search(query) if query else []
        self.art_listbox.delete(0, "end")
        for item in self._art_results:
            self.art_listbox.insert("end", f"{item['name']:40s}  |  {item['item_type']}")
        self._hide_detail()

    def _select_article(self):
        sel = self.art_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._art_results):
            return
        item = self._art_results[idx]
        self._selected_article = item
        if item["item_type"] == "Material":
            self._show_material_detail(item)
        else:
            self._show_tool_detail(item)

    # ===================== DETAIL-PANEL =====================
    def _build_detail_panel(self, parent):
        self.detail_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.detail_container.pack(fill="x", padx=10, pady=4)
        self._mat_detail = ctk.CTkFrame(self.detail_container, fg_color="transparent")
        self._tool_detail = ctk.CTkFrame(self.detail_container, fg_color="transparent")

        # Material-Details
        ctk.CTkLabel(self._mat_detail, text="Länge (cm):", font=("Segoe UI", 10)).grid(row=0, column=0, padx=4, pady=4)
        self.dl_length = ctk.CTkEntry(self._mat_detail, width=70)
        self.dl_length.grid(row=0, column=1, padx=4, pady=4)
        self.dl_length.bind("<KeyRelease>", lambda e: self._calc_detail_qm())
        ctk.CTkLabel(self._mat_detail, text="Breite (cm):", font=("Segoe UI", 10)).grid(row=0, column=2, padx=4, pady=4)
        self.dl_width = ctk.CTkEntry(self._mat_detail, width=70)
        self.dl_width.grid(row=0, column=3, padx=4, pady=4)
        self.dl_width.bind("<KeyRelease>", lambda e: self._calc_detail_qm())
        ctk.CTkLabel(self._mat_detail, text="Menge:", font=("Segoe UI", 10)).grid(row=0, column=4, padx=4, pady=4)
        self.dl_qty = ctk.CTkEntry(self._mat_detail, width=60)
        self.dl_qty.insert(0, "1")
        self.dl_qty.grid(row=0, column=5, padx=4, pady=4)
        self.dl_qty.bind("<KeyRelease>", lambda e: self._calc_detail_qm())
        ctk.CTkLabel(self._mat_detail, text="m²:", font=("Segoe UI", 10, "bold"),
                     text_color=("#8b0000", "#8b0000")).grid(row=0, column=6, padx=4, pady=4)
        self.dl_qm_label = ctk.CTkLabel(self._mat_detail, text="0,00", font=("Segoe UI", 10, "bold"))
        self.dl_qm_label.grid(row=0, column=7, padx=4, pady=4)
        ctk.CTkButton(self._mat_detail, text="Einfügen", command=self._insert_material,
                       width=80).grid(row=0, column=8, padx=10, pady=4)

        # Werkzeug-Details
        ctk.CTkLabel(self._tool_detail, text="Zeit:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=4, pady=4)
        self.dl_time = ctk.CTkEntry(self._tool_detail, width=70)
        self.dl_time.insert(0, "1")
        self.dl_time.grid(row=0, column=1, padx=4, pady=4)
        self.dl_time_unit = ctk.StringVar(value="h")
        ctk.CTkOptionMenu(self._tool_detail, variable=self.dl_time_unit, values=["h", "min"],
                          width=60).grid(row=0, column=2, padx=4, pady=4)
        ctk.CTkButton(self._tool_detail, text="Einfügen", command=self._insert_tool,
                       width=80).grid(row=0, column=3, padx=10, pady=4)

    def _show_material_detail(self, item):
        self._tool_detail.pack_forget()
        self._mat_detail.pack(fill="x")
        self._selected_article = item

    def _show_tool_detail(self, item):
        self._mat_detail.pack_forget()
        self._tool_detail.pack(fill="x")
        self._selected_article = item

    def _hide_detail(self):
        self._mat_detail.pack_forget()
        self._tool_detail.pack_forget()
        self._selected_article = None

    def _calc_detail_qm(self):
        try:
            length = float(self.dl_length.get().replace(",", ".")) / 100
            width = float(self.dl_width.get().replace(",", ".")) / 100
            qty = float(self.dl_qty.get().replace(",", "."))
            qm = length * width * qty
            self.dl_qm_label.configure(text=f"{qm:.2f}".replace(".", ","))
        except ValueError:
            self.dl_qm_label.configure(text="0,00")

    def _insert_material(self):
        item = self._selected_article
        if not item:
            return
        try:
            length = float(self.dl_length.get().replace(",", ".")) if self.dl_length.get() else 0
            width = float(self.dl_width.get().replace(",", ".")) if self.dl_width.get() else 0
            qty = float(self.dl_qty.get().replace(",", ".")) if self.dl_qty.get() else 1
        except ValueError:
            length = width = qty = 0
        price_m2 = item.get("price_per_m2", 0) or item.get("price", 0)
        if length > 0 and width > 0:
            qm = (length / 100) * (width / 100) * qty
            desc = f"{item['name']} ({length:.0f}x{width:.0f}cm x{qty:.0f})"
            total = qm * price_m2
            self._positions.append(PositionItem(
                "material", item["id"], desc, qm, "m\u00b2", price_m2, total,
                {"length": length, "width": width, "qty": qty}
            ))
        else:
            self._positions.append(PositionItem(
                "material", item["id"], item["name"], 1, "m\u00b2", price_m2, price_m2
            ))
        self._refresh_positions()
        self._hide_detail()
        self.art_var.set("")

    def _insert_tool(self):
        item = self._selected_article
        if not item:
            return
        try:
            time_val = float(self.dl_time.get().replace(",", "."))
        except ValueError:
            time_val = 1
        unit = self.dl_time_unit.get()
        price = item.get("price", 0)
        if unit == "min":
            price_per = price / 60
        else:
            price_per = price
        unit_label = "Std." if unit == "h" else "Min."
        total = time_val * price_per
        desc = f"{item['name']} ({time_val:.0f}{unit_label[0]})"
        self._positions.append(PositionItem(
            "tool", item["id"], desc, time_val, unit_label, price_per, total
        ))
        self._refresh_positions()
        self._hide_detail()
        self.art_var.set("")

    # ===================== POSITIONEN =====================
    def _refresh_positions(self):
        for row in self.pos_tree.get_children():
            self.pos_tree.delete(row)
        for i, p in enumerate(self._positions):
            qty_str = f"{p.quantity:.2f}" if p.quantity != int(p.quantity) else str(int(p.quantity))
            self.pos_tree.insert("", "end", iid=str(i), values=(
                str(i + 1), p.description, qty_str, p.unit,
                f"{p.price_per_unit:.2f}\u20ac", f"{p.total:.2f}\u20ac"
            ))
        self._recalc_totals()

    def _remove_selected_position(self):
        sel = self.pos_tree.selection()
        if sel:
            idx = int(sel[0])
            if 0 <= idx < len(self._positions):
                self._positions.pop(idx)
                self._refresh_positions()

    # ===================== SUMMEN =====================
    def _recalc_totals(self):
        settings = self.db.settings_get_all()
        tax_rate = float(settings.get("tax_rate", "19"))
        total_net = sum(p.total for p in self._positions)
        try:
            discount_val = float(self.discount_var.get().replace(",", "."))
        except ValueError:
            discount_val = 0
        if discount_val > 0:
            total_net = total_net * (1 - discount_val / 100)
        total_tax = total_net * tax_rate / 100
        total_gross = total_net + total_tax
        self._sum_labels["netto"].configure(text=f"{total_net:.2f}\u20ac".replace(".", ","))
        self._sum_labels["mwst"].configure(text=f"{total_tax:.2f}\u20ac".replace(".", ","))
        self._sum_labels["brutto"].configure(text=f"{total_gross:.2f}\u20ac".replace(".", ","))

    # ===================== FOOTER =====================
    def _build_footer(self, parent):
        lf = ctk.CTkFrame(parent, fg_color="transparent")
        lf.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ctk.CTkLabel(lf, text="Notiz:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 5))
        self.doc_note = ctk.CTkEntry(lf, width=250)
        self.doc_note.pack(side="left", padx=5)
        ctk.CTkLabel(lf, text="Rabatt %:", font=("Segoe UI", 10)).pack(side="left", padx=(15, 5))
        self.discount_var = ctk.StringVar(value="0")
        self.discount_entry = ctk.CTkEntry(lf, width=50, textvariable=self.discount_var)
        self.discount_entry.pack(side="left", padx=5)
        self.discount_entry.bind("<KeyRelease>", lambda e: self._recalc_totals())

        rf = ctk.CTkFrame(parent, fg_color="transparent")
        rf.pack(side="right", padx=8, pady=6)
        self._sum_labels = {}
        for text in ["Netto:", "MwSt.:", "Brutto:"]:
            f = ctk.CTkFrame(rf, fg_color="transparent")
            f.pack(side="left", padx=10)
            ctk.CTkLabel(f, text=text, font=("Segoe UI", 10)).pack(side="left")
            lbl = ctk.CTkLabel(f, text="0,00 \u20ac", font=("Segoe UI", 10, "bold"),
                               text_color=("#8b0000", "#8b0000"), width=70, anchor="e")
            lbl.pack(side="left", padx=4)
            key = text.replace(":", "").replace(" ", "_").lower()
            self._sum_labels[key] = lbl

        bf = ctk.CTkFrame(parent, fg_color="transparent")
        bf.pack(side="bottom", fill="x", padx=8, pady=6)
        actions = [
            ("Neu", self._new_doc),
            ("\xd6ffnen", self._open_doc_search),
            ("Speichern", self._save_doc),
            ("PDF", self._save_pdf),
            ("E-Mail", self._send_email_doc),
            ("Drucken", self._print_doc),
            ("L\xf6schen", self._delete_doc),
        ]
        for text, cmd in actions:
            fg = "#5c0000" if text in ["L\xf6schen"] else "#8b0000"
            ctk.CTkButton(bf, text=text, command=cmd, width=80,
                          fg_color=fg, hover_color="#b22222",
                          font=("Segoe UI", 10)).pack(side="left", padx=3)

    # ===================== DOKUMENT-LOGIK =====================
    def _new_doc(self):
        self._current_doc_id = None
        self._positions.clear()
        self._refresh_positions()
        self.cust_var.set("")
        self.art_var.set("")
        self.doc_note.delete(0, "end")
        self.discount_var.set("0")
        self.doc_type_var.set("RG")
        self._customer_id = None
        self._cust_data = []
        self.cust_listbox.delete(0, "end")

    def _get_doc_data(self):
        settings = self.db.settings_get_all()
        tax_rate = float(settings.get("tax_rate", "19"))
        total_net = sum(p.total for p in self._positions)
        try:
            discount_val = float(self.discount_var.get().replace(",", "."))
        except ValueError:
            discount_val = 0
        if discount_val > 0:
            net_after = total_net * (1 - discount_val / 100)
        else:
            net_after = total_net
        total_tax = net_after * tax_rate / 100
        total_gross = net_after + total_tax
        return {
            "doc_type": self.doc_type_var.get(),
            "customer_id": self._get_selected_customer_id(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "discount_type": "percent",
            "discount_value": discount_val,
            "total_net": net_after,
            "total_tax": total_tax,
            "total_gross": total_gross,
            "note": self.doc_note.get(),
        }

    def _save_doc(self):
        cid = self._get_selected_customer_id()
        if not cid:
            messagebox.showwarning("Fehler", "Bitte wählen Sie einen Kunden aus.")
            return
        if not self._positions:
            messagebox.showwarning("Fehler", "Keine Positionen vorhanden.")
            return
        data = self._get_doc_data()
        pos_data = []
        for p in self._positions:
            pos_data.append({
                "pos_type": p.pos_type,
                "ref_id": p.ref_id,
                "description": p.description,
                "quantity": p.quantity,
                "unit": p.unit,
                "price_per_unit": p.price_per_unit,
                "total": p.total,
            })
        data["id"] = self._current_doc_id
        result = self.db.doc_save(data, pos_data)
        if result:
            self._current_doc_id = result["id"]
            self.logger.info(f"Dokument {result['doc_number']} gespeichert")
            messagebox.showinfo("Gespeichert", f"{'Rechnung' if result['doc_type'] == 'RG' else 'Lieferschein'} {result['doc_number']} gespeichert.")
            self._load_doc(result["id"])

    def _load_doc(self, doc_id):
        doc = self.db.doc_get(doc_id)
        if not doc:
            return
        self._current_doc_id = doc["id"]
        self.doc_type_var.set(doc["doc_type"])
        self.doc_note.delete(0, "end")
        self.doc_note.insert(0, doc.get("note", ""))
        self.discount_var.set(str(doc.get("discount_value", "0")).replace(".", ","))
        customer = doc.get("customer")
        if customer:
            self._customer_id = customer["id"]
            name = customer.get("company") or f"{customer.get('last_name', '')} {customer.get('first_name', '')}".strip()
            self.cust_var.set(name)
        self._positions.clear()
        for p in doc.get("positions", []):
            self._positions.append(PositionItem(
                p["pos_type"], p["ref_id"], p["description"],
                p["quantity"], p["unit"], p["price_per_unit"], p["total"]
            ))
        self._refresh_positions()

    def _open_doc_search(self):
        DocSearchDialog(self)

    def _delete_doc(self):
        if not self._current_doc_id:
            return
        if messagebox.askyesno("Löschen", "Wirklich löschen?"):
            self.db.doc_delete(self._current_doc_id)
            self._new_doc()

    # ===================== PDF / E-MAIL / DRUCKEN =====================
    def _save_pdf(self):
        if not self._current_doc_id:
            messagebox.showwarning("Fehler", "Bitte zuerst speichern.")
            return
        doc = self.db.doc_get(self._current_doc_id)
        if not doc:
            return
        doc["app_name"] = APP_NAME
        path = generate_pdf(doc)
        if path:
            self.logger.info(f"PDF erstellt: {path}")
            if messagebox.askyesno("PDF", "PDF geöffnet? In Ordner öffnen?"):
                try:
                    os.startfile(os.path.dirname(path))
                except Exception:
                    pass

    def _send_email_doc(self):
        if not self._current_doc_id:
            messagebox.showwarning("Fehler", "Bitte zuerst speichern.")
            return
        doc = self.db.doc_get(self._current_doc_id)
        if not doc:
            return
        customer = doc.get("customer", {})
        recipient = customer.get("email", "")
        if not recipient:
            messagebox.showwarning("Fehler", "Kunde hat keine E-Mail-Adresse.")
            return
        doc["app_name"] = APP_NAME
        pdf_path = generate_pdf(doc)
        subject = f"{'Rechnung' if doc['doc_type'] == 'RG' else 'Lieferschein'} {doc['doc_number']}"
        body = f"Sehr geehrte Damen und Herren,\n\nanbei erhalten Sie die {'Rechnung' if doc['doc_type'] == 'RG' else 'den Lieferschein'} {doc['doc_number']}.\n\nMit freundlichen Grüßen\nFerdlWorks"
        success, msg = send_email(recipient, subject, body, pdf_path)
        if success:
            messagebox.showinfo("E-Mail", msg)
        else:
            messagebox.showerror("Fehler", msg)

    def _print_doc(self):
        if not self._current_doc_id:
            messagebox.showwarning("Fehler", "Bitte zuerst speichern.")
            return
        doc = self.db.doc_get(self._current_doc_id)
        if not doc:
            return
        doc["app_name"] = APP_NAME
        pdf_path = generate_pdf(doc)
        try:
            os.startfile(pdf_path, "print")
        except Exception as ex:
            messagebox.showerror("Fehler", f"Drucken fehlgeschlagen: {ex}")

    # ===================== MENÜ-ACTIONEN =====================
    def _open_customer_mgmt(self):
        CustomerDatabase(self)

    def _open_tool_mgmt(self):
        ToolDatabase(self)

    def _open_material_mgmt(self):
        MaterialDatabase(self)

    def _open_settings(self):
        SettingsDialog(self, master_mode=self._master_mode)

    def _backup_data(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Datensicherung speichern",
            defaultextension=".db",
            filetypes=[("Datenbank", "*.db")],
            initialfile=f"FerdlWorks_Backup_{datetime.now().strftime('%Y%m%d')}.db")
        if path:
            if self.db.backup_to(path):
                messagebox.showinfo("Sicherung", "Datenbank gesichert.")

    def _restore_data(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Datensicherung wiederherstellen",
            filetypes=[("Datenbank", "*.db")])
        if path:
            if messagebox.askyesno("Wiederherstellen", "Aktuelle Daten werden überschrieben. Fortfahren?"):
                if self.db.restore_from(path):
                    messagebox.showinfo("Wiederherstellung", "Datenbank wiederhergestellt.")
                    self._new_doc()

    def _cloud_gdrive(self):
        settings = self.db.settings_get_all()
        if not settings.get("gdrive_refresh_token"):
            if messagebox.askyesno("Google Drive", "Noch nicht autorisiert. Jetzt einrichten?"):
                success, msg = gdrive_authorize()
                if success:
                    messagebox.showinfo("Erfolg", msg)
                else:
                    messagebox.showerror("Fehler", msg)
            return
        success, msg = gdrive_backup(settings)
        if success:
            messagebox.showinfo("Google Drive", msg)
        else:
            messagebox.showerror("Fehler", msg)

    def _cloud_onedrive(self):
        settings = self.db.settings_get_all()
        if not settings.get("onedrive_refresh_token"):
            if messagebox.askyesno("OneDrive", "Noch nicht autorisiert. Jetzt einrichten?"):
                success, msg = onedrive_authorize()
                if success:
                    messagebox.showinfo("Erfolg", msg)
                else:
                    messagebox.showerror("Fehler", msg)
            return
        success, msg = onedrive_backup(settings)
        if success:
            messagebox.showinfo("OneDrive", msg)
        else:
            messagebox.showerror("Fehler", msg)

    def _open_log(self):
        log_path = get_log_path()
        try:
            os.startfile(log_path)
            self.logger.info(f"Logdatei geöffnet: {log_path}")
        except Exception as ex:
            self.logger.error(f"Konnte Logdatei nicht öffnen: {ex}")

    def _check_update(self):
        self.logger.info("Update-Prüfung gestartet")
        release, error = check_for_update()
        if error:
            messagebox.showerror("Update-Fehler", f"Konnte nicht nach Updates suchen:\n{error}")
            return
        if release is None:
            messagebox.showinfo("Aktuell", f"Sie haben die aktuellste Version v{VERSION}.")
            return
        tag = release.get("tag_name", "").lstrip("v")
        body = release.get("body", "Keine Details.")
        msg = f"Neue Version v{tag} verfügbar!\n\n{body[:500]}\n\nJetzt herunterladen und installieren?"
        if not messagebox.askyesno("Update verfügbar", msg):
            return
        dlg = ProgressDialog(self, "Update wird heruntergeladen...")
        dlg.show()
        path = download_installer(release, lambda p: dlg.set_progress(p))
        dlg.close()
        if path:
            if install_update(path):
                self.logger.info(f"Update auf v{tag} gestartet")
                sys.exit(0)
            else:
                messagebox.showerror("Fehler", "Installation fehlgeschlagen.")
        else:
            messagebox.showerror("Fehler", "Download fehlgeschlagen.")

    def _uninstall(self):
        result = messagebox.askyesnocancel(
            "Deinstallation",
            "Möchten Sie FerdlWorks deinstallieren?\n\nJa = Einstellungen behalten\nNein = Alles löschen\nAbbrechen = Abbrechen")
        if result is None:
            return
        if not result:
            reg_delete_all()
        uninstall_path = reg_read("UninstallPath", "")
        if uninstall_path and os.path.exists(uninstall_path):
            subprocess.Popen([uninstall_path, "/SILENT"])
            self.destroy()
        else:
            messagebox.showerror("Fehler", "Kein Deinstallationsprogramm gefunden.")

    def _show_info(self):
        win = ctk.CTkToplevel(self)
        win.title("Info")
        win.geometry("350x200")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        ctk.CTkLabel(win, text=APP_NAME, font=("Segoe UI", 18, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(pady=(20, 5))
        ctk.CTkLabel(win, text=f"Version {VERSION}", font=("Segoe UI", 12)).pack()
        ctk.CTkLabel(win, text=COMPANY_NAME, font=("Segoe UI", 11),
                     text_color="#888888").pack(pady=(10, 0))
        ctk.CTkLabel(win, text="© 2026 Sonderegger Software", font=("Segoe UI", 10),
                     text_color="#666666").pack(pady=(5, 0))

    def _on_close(self):
        self.logger.info("Anwendung wird beendet")
        self.destroy()
        sys.exit(0)


# ===================== DOKUMENT-SUCHE =====================
class DocSearchDialog(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.db = get_db()
        self.app = master
        self.title("Dokumente suchen")
        self.geometry("700x450")
        self.transient(master)
        self.grab_set()
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Suchen:").pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(top, width=250, placeholder_text="Nr., Kunde...")
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._load_data())
        ctk.CTkLabel(top, text="Typ:").pack(side="left", padx=(15, 5))
        self.type_var = ctk.StringVar(value="all")
        ctk.CTkOptionMenu(top, values=["Alle", "RG", "LS"], variable=self.type_var,
                          command=lambda v: self._load_data(), width=70).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Öffnen", command=self._open_selected, width=80).pack(side="right", padx=5)
        ctk.CTkButton(top, text="Schließen", command=self.destroy, width=80).pack(side="right", padx=5)
        cols = ("doc", "kunde", "datum", "betrag")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("doc", text="Dokument")
        self.tree.heading("kunde", text="Kunde")
        self.tree.heading("datum", text="Datum")
        self.tree.heading("betrag", text="Betrag")
        self.tree.column("doc", width=150)
        self.tree.column("kunde", width=200)
        self.tree.column("datum", width=100)
        self.tree.column("betrag", width=100, anchor="e")
        self.tree.bind("<Double-1>", lambda e: self._open_selected())
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        vsb.pack(side="right", fill="y")
        vsb.place(in_=self.tree, relx=1.0, rely=0, relheight=1.0, x=0)
        self._docs = []

    def _load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._docs.clear()
        type_filter = {"Alle": None, "RG": "RG", "LS": "LS"}.get(self.type_var.get(), None)
        query = self.search_entry.get()
        self._docs = self.db.doc_search(type_filter, query)
        for doc in self._docs:
            cname = doc.get("customer_name", "")
            dtype = "RG" if doc["doc_type"] == "RG" else "LS"
            self.tree.insert("", "end", iid=str(doc["id"]), values=(
                f"{dtype} {doc['doc_number']}", cname, doc["date"],
                f"{doc.get('total_gross', 0):.2f}\u20ac".replace(".", ",")
            ))

    def _open_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        doc_id = int(sel[0])
        self.app._load_doc(doc_id)
        self.destroy()


class ProgressDialog:
    def __init__(self, master, title="Bitte warten..."):
        self.win = ctk.CTkToplevel(master)
        self.win.title(title)
        self.win.geometry("400x120")
        self.win.resizable(False, False)
        self.win.transient(master)
        self.win.grab_set()
        self.label = ctk.CTkLabel(self.win, text="Vorgang läuft...", font=("Segoe UI", 11))
        self.label.pack(pady=(15, 5))
        self.progress = ctk.CTkProgressBar(self.win, width=350, height=20,
                                           fg_color="#2a2a2a", progress_color="#8b0000")
        self.progress.pack(pady=10)
        self.progress.set(0)
        self.win.update()

    def show(self):
        self.win.deiconify()

    def set_progress(self, value):
        self.progress.set(value / 100)
        self.label.configure(text=f"{value:.0f}%")
        self.win.update()

    def close(self):
        try:
            self.win.destroy()
        except Exception:
            pass


def run_app():
    setup_logger()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme(THEME_PATH)
    root = ctk.CTk()
    root.withdraw()
    db = get_db()
    settings = db.settings_get_all()
    has_password = bool(settings.get("user_password", ""))
    if has_password:
        from lib.login_dialog import LoginDialog
        login = LoginDialog(root)
        root.wait_window(login)
        if not login.is_authenticated():
            root.destroy()
            return
        master_mode = login.is_master_mode()
    else:
        master_mode = False
    root.destroy()
    app = FerdlWorksApp(master_mode=master_mode)
    app.mainloop()


if __name__ == "__main__":
    run_app()
