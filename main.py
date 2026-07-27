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
from lib.database import get_db
from lib.settings_dialog import SettingsDialog
from lib.customer_dialog import CustomerDialog
from lib.customer_database import CustomerDatabase
from lib.tool_database import ToolDatabase
from lib.material_database import MaterialDatabase
from lib.text_database import TextDatabase
from lib.pdf_gen import generate_pdf
from lib.email_sender import send_email
from lib.updater import check_for_update, download_installer, install_update, install_and_restart
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
        self._editing_pos_idx = None
        self._build_menu()
        self._build_ui()
        self.bind("<Button-1>", self._on_global_click, add="+")
        self.logger.info(f"{APP_NAME} v{VERSION} gestartet (Master-Mode: {master_mode})")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ===================== MENÜ =====================
    def _build_menu(self):
        mb = tk.Menu(self, font=("Segoe UI", 10))
        datei = tk.Menu(mb, tearoff=False, font=("Segoe UI", 10))
        datei.add_command(label="Rechnungen & Lieferscheine...", command=self._open_doc_overview, accelerator="Strg+D")
        datei.add_separator()
        datei.add_command(label="Einstellungen...", command=self._open_settings, accelerator="Strg+E")
        datei.add_separator()
        backup = tk.Menu(datei, tearoff=False, font=("Segoe UI", 10))
        backup.add_command(label="Datensicherung erstellen...", command=self._backup_data)
        backup.add_command(label="Datensicherung wiederherstellen...", command=self._restore_data)
        backup.add_separator()
        backup.add_command(label="Google Drive Backup...", command=self._cloud_gdrive)
        backup.add_command(label="Microsoft OneDrive Backup...", command=self._cloud_onedrive)
        datei.add_cascade(label="Backup", menu=backup)
        datei.add_separator()
        datei.add_command(label="Beenden", command=self._on_close, accelerator="Strg+Q")
        mb.add_cascade(label="Datei", menu=datei)

        verw = tk.Menu(mb, tearoff=False, font=("Segoe UI", 10))
        verw.add_command(label="Kundenverwaltung...", command=self._open_customer_mgmt)
        verw.add_command(label="Materialverwaltung...", command=self._open_material_mgmt)
        verw.add_command(label="Werkzeugverwaltung...", command=self._open_tool_mgmt)
        verw.add_separator()
        verw.add_command(label="Texteverwaltung...", command=self._open_text_mgmt)
        mb.add_cascade(label="Verwaltung", menu=verw)

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
        self.bind_all("<Control-d>", lambda e: self._open_doc_overview())
        self.bind_all("<Control-q>", lambda e: self._on_close())
        self.bind_all("<Control-e>", lambda e: self._open_settings())
        self.bind_all("<Control-u>", lambda e: self._check_update())

    # ===================== UI =====================
    def _build_ui(self):
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Kunde (Entry + Dropdown) ---
        cust = ctk.CTkFrame(main, corner_radius=6)
        cust.pack(fill="x", padx=8, pady=(4, 1))
        
        # Top row: Label + Entry + Buttons
        cust_top = ctk.CTkFrame(cust, fg_color="transparent")
        cust_top.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(cust_top, text="Kunde:", font=("Segoe UI", 11, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(side="left", padx=(0, 5))
        self.cust_entry = ctk.CTkEntry(cust_top, width=500, placeholder_text="Kunde eingeben...")
        self.cust_entry.bind("<KeyRelease>", lambda e: self._filter_customers() if e.keysym not in ("Up", "Down", "Return", "Escape") else None)
        self.cust_entry.pack(side="left", padx=5)
        # Buttons Neu / Bearbeiten
        self.cust_btn_new = ctk.CTkButton(cust_top, text="Neu", width=60, 
                                          command=self._new_customer_from_main,
                                          fg_color="#5c0000", hover_color="#8b0000")
        self.cust_btn_new.pack(side="left", padx=5)
        self.cust_btn_edit = ctk.CTkButton(cust_top, text="Bearbeiten", width=80, 
                                           command=self._edit_customer_from_main, state="disabled",
                                           fg_color="#5c0000", hover_color="#8b0000")
        self.cust_btn_edit.pack(side="left", padx=5)
        self.doc_type_var = ctk.StringVar(value="RG")

        # Dropdown-Liste Kunde (schwebend über anderen Elementen)
        self._cust_dropdown_frame = tk.Frame(self, bg="#2a2a2a", highlightbackground="#555555", highlightthickness=1)
        self.cust_dropdown = tk.Listbox(self._cust_dropdown_frame, height=5,
                                        font=("Segoe UI", 10), exportselection=False,
                                        bg="#2a2a2a", fg="#e0e0e0", selectbackground="#8b0000",
                                        borderwidth=0, highlightthickness=0)
        self.cust_dropdown.pack(fill="x", padx=2, pady=2)
        self.cust_dropdown.bind("<<ListboxSelect>>", lambda e: self._pick_customer())
        # Tastatur-Navigation
        self.cust_entry.bind("<Down>", lambda e: self._nav_cust_down())
        self.cust_entry.bind("<Up>", lambda e: self._nav_cust_up())
        self.cust_entry.bind("<Return>", lambda e: self._enter_cust())
        self.cust_entry.bind("<Escape>", lambda e: self._do_hide_cust_dropdown())
        self._cust_data = []
        self._customer_id = None
        self._cust_dropdown_idx = -1

        # --- Artikel-Suche (Entry + Dropdown + Einheiten) ---
        art = ctk.CTkFrame(main, corner_radius=6)
        art.pack(fill="x", padx=8, pady=1)
        ctk.CTkLabel(art, text="Artikel:", font=("Segoe UI", 11, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(side="left", padx=(10, 5))
        self.art_entry = ctk.CTkEntry(art, width=500, placeholder_text="Werkzeug, Material oder Text eingeben...")
        self.art_entry.pack(side="left", padx=5, pady=4)
        self.art_entry.bind("<KeyRelease>", lambda e: self._search_articles() if e.keysym not in ("Up", "Down", "Return", "Escape") else None)

        # Kontext-Felder (abhängig vom ausgewählten Artikel-Typ, versteckt)
        self._art_mat_f = ctk.CTkFrame(art, fg_color="transparent")
        ctk.CTkLabel(self._art_mat_f, text="L:", font=("Segoe UI", 10)).pack(side="left")
        self.dl_length = ctk.CTkEntry(self._art_mat_f, width=55)
        self.dl_length.pack(side="left", padx=2)
        self.dl_length.bind("<KeyRelease>", lambda e: self._calc_detail_qm())
        ctk.CTkLabel(self._art_mat_f, text="cm", font=("Segoe UI", 9, "bold"),
                     text_color=("#666666", "#888888")).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(self._art_mat_f, text="B:", font=("Segoe UI", 10)).pack(side="left")
        self.dl_width = ctk.CTkEntry(self._art_mat_f, width=55)
        self.dl_width.pack(side="left", padx=2)
        self.dl_width.bind("<KeyRelease>", lambda e: self._calc_detail_qm())
        ctk.CTkLabel(self._art_mat_f, text="cm", font=("Segoe UI", 9, "bold"),
                     text_color=("#666666", "#888888")).pack(side="left", padx=(0, 4))
        self.dl_qm_label = ctk.CTkLabel(self._art_mat_f, text="m\xb2:0,00", font=("Segoe UI", 9, "bold"),
                                        text_color=("#8b0000", "#8b0000"))
        self.dl_qm_label.pack(side="left", padx=2)

        self._art_tool_f = ctk.CTkFrame(art, fg_color="transparent")
        ctk.CTkLabel(self._art_tool_f, text="Zeit:", font=("Segoe UI", 10)).pack(side="left")
        self.dl_time = ctk.CTkEntry(self._art_tool_f, width=55)
        self.dl_time.insert(0, "1")
        self.dl_time.pack(side="left", padx=2)
        self.dl_time_unit = ctk.StringVar(value="h")
        ctk.CTkOptionMenu(self._art_tool_f, variable=self.dl_time_unit, values=["h", "min"],
                          width=55).pack(side="left", padx=2)

        self.art_insert_btn = ctk.CTkButton(art, text="Einfügen", command=self._insert_article,
                                            width=80, fg_color="#5c0000", hover_color="#8b0000")
        self.art_insert_btn.pack(side="right", padx=5)

        self.art_text_btn = ctk.CTkButton(art, text="Als Text eintragen", command=self._insert_as_text,
                                          width=140, fg_color="#555555", hover_color="#777777")
        self.art_text_btn.pack(side="right", padx=2)
        self.art_text_btn.pack_forget()  # erstmal unsichtbar

        # Dropdown-Liste Artikel (schwebend über anderen Elementen)
        self._art_dropdown_frame = tk.Frame(self, bg="#2a2a2a", highlightbackground="#555555", highlightthickness=1)
        self.art_dropdown = tk.Listbox(self._art_dropdown_frame, height=5,
                                       font=("Segoe UI", 10), exportselection=False,
                                       bg="#2a2a2a", fg="#e0e0e0", selectbackground="#8b0000",
                                       borderwidth=0, highlightthickness=0)
        self.art_dropdown.pack(fill="x", padx=2, pady=2)
        self.art_dropdown.bind("<<ListboxSelect>>", lambda e: self._select_article())
        self.art_entry.bind("<Down>", lambda e: self._nav_art_down())
        self.art_entry.bind("<Up>", lambda e: self._nav_art_up())
        self.art_entry.bind("<Return>", lambda e: self._enter_art())
        self.art_entry.bind("<Escape>", lambda e: self._do_hide_art_dropdown())
        self._art_results = []
        self._selected_article = None
        self._art_dropdown_idx = -1
        self._hide_units()

        # --- Positionen (unten) ---
        pos_frame = ctk.CTkFrame(main, corner_radius=6)
        pos_frame.pack(fill="both", expand=True, padx=8, pady=2)
        ctk.CTkLabel(pos_frame, text="Positionen", font=("Segoe UI", 11, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(anchor="w", padx=10, pady=(6, 2))
        cols = ("pos", "beschreibung", "menge", "einheit", "ep", "gesamt")
        heads = {"pos": "Pos.", "beschreibung": "Beschreibung", "menge": "Menge",
                 "einheit": "Einheit", "ep": "EP", "gesamt": "Gesamt"}
        widths = {"pos": 40, "beschreibung": 350, "menge": 60, "einheit": 60, "ep": 80, "gesamt": 90}
        self.pos_tree = ttk.Treeview(pos_frame, columns=cols, show="headings", height=5)
        for c in cols:
            self.pos_tree.heading(c, text=heads[c])
            self.pos_tree.column(c, width=widths[c], minwidth=30, anchor="w" if c in ("pos", "beschreibung") else "e")
        self.pos_tree.bind("<Delete>", lambda e: self._remove_selected_position())
        self.pos_tree.bind("<Double-1>", lambda e: self._edit_position())
        self.pos_tree.bind("<Button-3>", self._pos_context_menu)
        self.pos_tree.bind("<Button-2>", self._pos_context_menu)
        vsb = ttk.Scrollbar(pos_frame, orient="vertical", command=self.pos_tree.yview)
        self.pos_tree.configure(yscrollcommand=vsb.set)
        self.pos_tree.pack(fill="both", expand=True, padx=10, pady=2)
        vsb.pack(side="right", fill="y")
        vsb.place(in_=self.pos_tree, relx=1.0, rely=0, relheight=1.0, x=0)

        # --- Footer ---
        footer = ctk.CTkFrame(main, corner_radius=6)
        footer.pack(fill="x", padx=8, pady=4)
        self._build_footer(footer)

        # --- Status Bar ---
        self._build_statusbar()

    # ===================== KUNDEN-DROPDOWN =====================
    def _on_global_click(self, event):
        w = self.winfo_containing(event.x_root, event.y_root)
        if self._cust_dropdown_frame.winfo_viewable():
            if w not in (self.cust_entry, self.cust_dropdown, self._cust_dropdown_frame) \
               and getattr(w, 'master', None) not in (self._cust_dropdown_frame,):
                self._do_hide_cust_dropdown()
        if self._art_dropdown_frame.winfo_viewable():
            if w not in (self.art_entry, self.art_dropdown, self._art_dropdown_frame) \
               and getattr(w, 'master', None) not in (self._art_dropdown_frame,):
                self._do_hide_art_dropdown()

    def _set_cust_display(self, cust):
        parts = [cust.get("company") or f"{cust.get('last_name', '')} {cust.get('first_name', '')}".strip()]
        if cust.get("street"):
            parts.append(cust["street"])
        zc = " ".join(filter(None, [cust.get("zip", ""), cust.get("city", "")]))
        if zc:
            parts.append(zc)
        self.cust_entry.delete(0, "end")
        self.cust_entry.insert(0, ", ".join(parts))

    def _filter_customers(self):
        query = self.cust_entry.get().strip()
        self._cust_data = self.db.customer_search(query) if query else []
        self.cust_dropdown.delete(0, "end")
        for c in self._cust_data:
            name = c.get("company") or f"{c.get('last_name', '')} {c.get('first_name', '')}".strip()
            orts = c.get("city", "")
            self.cust_dropdown.insert("end", f"{name}  ({orts})" if orts else name)
        if query and self._cust_data:
            self._show_cust_dropdown()
        else:
            self._do_hide_cust_dropdown()

    def _show_cust_dropdown(self):
        self._cust_dropdown_idx = -1
        x = self.cust_entry.winfo_rootx() - self.winfo_rootx()
        y = self.cust_entry.winfo_rooty() - self.winfo_rooty() + self.cust_entry.winfo_height()
        self._cust_dropdown_frame.place(x=x, y=y, width=500, anchor="nw")

    def _do_hide_cust_dropdown(self):
        self._cust_dropdown_frame.place_forget()
        self.cust_dropdown.selection_clear(0, "end")

    def _nav_cust_down(self, event=None):
        if not self._cust_data or not self._cust_dropdown_frame.winfo_viewable():
            return
        n = len(self._cust_data)
        if self._cust_dropdown_idx >= n - 1:
            return
        self._cust_dropdown_idx += 1
        idx = self._cust_dropdown_idx
        self.cust_dropdown.selection_clear(0, "end")
        self.cust_dropdown.selection_set(idx)
        self.cust_dropdown.activate(idx)
        self.cust_dropdown.see(idx)

    def _nav_cust_up(self, event=None):
        if not self._cust_data or not self._cust_dropdown_frame.winfo_viewable():
            return
        if self._cust_dropdown_idx <= 0:
            return
        self._cust_dropdown_idx -= 1
        idx = self._cust_dropdown_idx
        self.cust_dropdown.selection_clear(0, "end")
        self.cust_dropdown.selection_set(idx)
        self.cust_dropdown.activate(idx)
        self.cust_dropdown.see(idx)

    def _enter_cust(self, event=None):
        if self._cust_dropdown_idx < 0 or self._cust_dropdown_idx >= len(self._cust_data):
            return
            self._customer_id = self._cust_data[self._cust_dropdown_idx]["id"]
            self._set_cust_display(self._cust_data[self._cust_dropdown_idx])
            self.cust_btn_edit.configure(state="normal")
        self._do_hide_cust_dropdown()

    def _nav_art_down(self, event=None):
        if not self._art_results or not self._art_dropdown_frame.winfo_viewable():
            return
        n = len(self._art_results)
        if self._art_dropdown_idx >= n - 1:
            return
        self._art_dropdown_idx += 1
        idx = self._art_dropdown_idx
        self.art_dropdown.selection_clear(0, "end")
        self.art_dropdown.selection_set(idx)
        self.art_dropdown.activate(idx)
        self.art_dropdown.see(idx)

    def _nav_art_up(self, event=None):
        if not self._art_results or not self._art_dropdown_frame.winfo_viewable():
            return
        if self._art_dropdown_idx <= 0:
            return
        self._art_dropdown_idx -= 1
        idx = self._art_dropdown_idx
        self.art_dropdown.selection_clear(0, "end")
        self.art_dropdown.selection_set(idx)
        self.art_dropdown.activate(idx)
        self.art_dropdown.see(idx)

    def _enter_art(self, event=None):
        if self._art_dropdown_idx < 0 or self._art_dropdown_idx >= len(self._art_results):
            return
        self._selected_article = self._art_results[self._art_dropdown_idx]
        self.art_entry.delete(0, "end")
        self.art_entry.insert(0, self._selected_article["name"])
        self._do_hide_art_dropdown()
        if self._selected_article["item_type"] == "Material":
            self._show_mat_units()
        elif self._selected_article["item_type"] == "Werkzeug":
            self._show_tool_units()
        else:
            self._hide_units()

    def _pick_customer(self):
        sel = self.cust_dropdown.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._cust_data):
            self._cust_dropdown_idx = idx
            self._customer_id = self._cust_data[idx]["id"]
            self._set_cust_display(self._cust_data[idx])
            self._do_hide_cust_dropdown()

    def _get_selected_customer_id(self):
        return self._customer_id

    def _new_customer_from_main(self):
        dlg = CustomerDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._customer_id = dlg.result["id"]
            self._set_cust_display(dlg.result)

    def _edit_customer_from_main(self):
        cid = self._get_selected_customer_id()
        if not cid:
            messagebox.showinfo("Hinweis", "Kein Kunde ausgewählt.")
            return
        dlg = CustomerDialog(self, customer_id=cid)
        self.wait_window(dlg)
        if dlg.result:
            self._set_cust_display(dlg.result)

    # ===================== ARTIKEL-DROPDOWN =====================
    def _search_articles(self):
        query = self.art_entry.get().strip()
        self._art_results = self.db.combined_search(query) if query else []
        self.art_dropdown.delete(0, "end")
        for item in self._art_results:
            self.art_dropdown.insert("end", f"{item['item_type']:10s} | {item['name']}")
        if query and self._art_results:
            self._show_art_dropdown()
            self.art_text_btn.pack_forget()
        elif query and not self._art_results:
            self._do_hide_art_dropdown()
            self.art_text_btn.pack(side="right", padx=2)
        else:
            self._do_hide_art_dropdown()
            self.art_text_btn.pack_forget()

    def _show_art_dropdown(self):
        self._art_dropdown_idx = -1
        x = self.art_entry.winfo_rootx() - self.winfo_rootx()
        y = self.art_entry.winfo_rooty() - self.winfo_rooty() + self.art_entry.winfo_height()
        self._art_dropdown_frame.place(x=x, y=y, width=500, anchor="nw")

    def _do_hide_art_dropdown(self):
        self._art_dropdown_frame.place_forget()
        self.art_dropdown.selection_clear(0, "end")

    def _select_article(self):
        sel = self.art_dropdown.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self._art_results):
            return
        self._art_dropdown_idx = idx
        self._selected_article = self._art_results[idx]
        self.art_entry.delete(0, "end")
        self.art_entry.insert(0, self._selected_article["name"])
        self._do_hide_art_dropdown()
        if self._selected_article["item_type"] == "Material":
            self._show_mat_units()
        elif self._selected_article["item_type"] == "Werkzeug":
            self._show_tool_units()
        else:
            self._hide_units()

    def _show_mat_units(self):
        self._art_tool_f.pack_forget()
        self._art_mat_f.pack(side="left", padx=(5, 0))
        self.art_insert_btn.configure(text="Übernehmen" if self._editing_pos_idx is not None else "Einfügen")
        self.dl_length.delete(0, "end")
        self.dl_width.delete(0, "end")

    def _show_tool_units(self):
        self._art_mat_f.pack_forget()
        self._art_tool_f.pack(side="left", padx=(5, 0))
        self.art_insert_btn.configure(text="Übernehmen" if self._editing_pos_idx is not None else "Einfügen")
        self.dl_time.delete(0, "end")
        self.dl_time.insert(0, "1")

    def _hide_units(self):
        self._art_mat_f.pack_forget()
        self._art_tool_f.pack_forget()

    def _calc_detail_qm(self):
        try:
            length = float(self.dl_length.get().replace(",", ".")) / 100
            width = float(self.dl_width.get().replace(",", ".")) / 100
            qm = length * width
            self.dl_qm_label.configure(text=f"m\xb2:{qm:.2f}".replace(".", ","))
        except ValueError:
            self.dl_qm_label.configure(text="m\xb2:0,00")

    # ===================== EINFÜGEN / ÜBERNEHMEN =====================
    def _calc_tool_position(self, item):
        try:
            time_val = float(self.dl_time.get().replace(",", "."))
        except ValueError:
            time_val = 1
        display_unit = self.dl_time_unit.get()
        stored_unit = item.get("price_unit", "h")
        price = item.get("price", 0)
        rate_per_min = price / 60 if stored_unit == "h" else price
        minutes = time_val * 60 if display_unit == "h" else time_val
        total = minutes * rate_per_min
        price_per_display = rate_per_min * 60 if display_unit == "h" else rate_per_min
        unit_label = "Std." if display_unit == "h" else "Min."
        return time_val, unit_label, price_per_display, total, int(minutes)

    def _insert_as_text(self):
        text = self.art_entry.get().strip()
        if not text:
            return
        self._positions.append(PositionItem("text", None, text, 0, "", 0, 0))
        self._refresh_positions()
        self._hide_units()
        self.art_entry.delete(0, "end")
        self.art_text_btn.pack_forget()

    def _insert_article(self):
        if self._editing_pos_idx is not None:
            self._update_position()
        else:
            self._add_position()
        self._refresh_positions()
        self._hide_units()
        self._selected_article = None
        self.art_entry.delete(0, "end")

    def _add_position(self):
        item = self._selected_article
        if not item:
            return
        if item["item_type"] == "Material":
            try:
                length = float(self.dl_length.get().replace(",", ".")) if self.dl_length.get() else 0
                width = float(self.dl_width.get().replace(",", ".")) if self.dl_width.get() else 0
            except ValueError:
                length = width = 0
            price_m2 = item.get("price_per_m2", 0) or item.get("price", 0)
            if length > 0 and width > 0:
                qm = (length / 100) * (width / 100)
                desc = f"{item['name']} ({length:.0f}x{width:.0f}cm)"
                total = qm * price_m2
                self._positions.append(PositionItem(
                    "material", item["id"], desc, qm, "m\u00b2", price_m2, total,
                    {"length": length, "width": width, "qty": 1}
                ))
            else:
                self._positions.append(PositionItem(
                    "material", item["id"], item["name"], 1, "m\u00b2", price_m2, price_m2
                ))
        elif item["item_type"] == "Werkzeug":
            time_val, unit_label, price_per, total, _ = self._calc_tool_position(item)
            desc = item["name"]
            self._positions.append(PositionItem(
                "tool", item["id"], desc, time_val, unit_label, price_per, total,
                {"price_unit": item.get("price_unit", "h"), "price": item.get("price", 0)}
            ))
        elif item["item_type"] == "Text":
            desc = item.get("content") or item["name"]
            self._positions.append(PositionItem(
                "text", item["id"], desc, 0, "", 0, 0
            ))

    def _update_position(self):
        item = self._selected_article
        if not item:
            return
        idx = self._editing_pos_idx
        if item["item_type"] == "Material":
            try:
                length = float(self.dl_length.get().replace(",", ".")) if self.dl_length.get() else 0
                width = float(self.dl_width.get().replace(",", ".")) if self.dl_width.get() else 0
            except ValueError:
                length = width = 0
            price_m2 = item.get("price_per_m2", 0) or item.get("price", 0)
            if length > 0 and width > 0:
                qm = (length / 100) * (width / 100)
                desc = f"{item['name']} ({length:.0f}x{width:.0f}cm)"
                total = qm * price_m2
                self._positions[idx] = PositionItem(
                    "material", item["id"], desc, qm, "m\u00b2", price_m2, total,
                    {"length": length, "width": width, "qty": 1}
                )
            else:
                self._positions[idx] = PositionItem(
                    "material", item["id"], item["name"], 1, "m\u00b2", price_m2, price_m2
                )
        elif item["item_type"] == "Werkzeug":
            time_val, unit_label, price_per, total, _ = self._calc_tool_position(item)
            desc = item["name"]
            self._positions[idx] = PositionItem(
                "tool", item["id"], desc, time_val, unit_label, price_per, total,
                {"price_unit": item.get("price_unit", "h"), "price": item.get("price", 0)}
            )
        elif item["item_type"] == "Text":
            desc = item.get("content") or item["name"]
            self._positions[idx] = PositionItem(
                "text", item["id"], desc, 0, "", 0, 0
            )
        self._editing_pos_idx = None
        self.art_insert_btn.configure(text="Einfügen")

    # ===================== POSITIONEN =====================
    def _refresh_positions(self):
        for row in self.pos_tree.get_children():
            self.pos_tree.delete(row)
        for i, p in enumerate(self._positions):
            qty_str = f"{p.quantity:.2f}" if p.quantity != int(p.quantity) else str(int(p.quantity))
            if p.pos_type == "tool" and p.extra_data and "price_unit" in p.extra_data:
                ep_str = f"{p.extra_data['price']:.2f}\u20ac/{p.extra_data['price_unit']}"
            elif p.pos_type == "text":
                ep_str = ""
            else:
                ep_str = f"{p.price_per_unit:.2f}\u20ac/{p.unit.lower().replace('std.', 'h').replace('min.', 'min')}"
            if p.pos_type == "text":
                vals = ("", p.description, "", "", "", "")
            else:
                vals = (str(i + 1), p.description, qty_str, p.unit, ep_str, f"{p.total:.2f}\u20ac")
            self.pos_tree.insert("", "end", iid=str(i), values=vals)
        self._recalc_totals()

    def _pos_context_menu(self, event):
        # select the clicked row
        iid = self.pos_tree.identify_row(event.y)
        if not iid:
            return
        self.pos_tree.selection_set(iid)
        menu = tk.Menu(self, tearoff=False, font=("Segoe UI", 10))
        menu.add_command(label="Bearbeiten", command=self._edit_position)
        menu.add_command(label="Löschen", command=self._remove_selected_position)
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def _remove_selected_position(self):
        sel = self.pos_tree.selection()
        if sel:
            idx = int(sel[0])
            if 0 <= idx < len(self._positions):
                self._positions.pop(idx)
                self._refresh_positions()

    def _edit_position(self):
        sel = self.pos_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        if idx >= len(self._positions):
            return
        pos = self._positions[idx]
        self._editing_pos_idx = idx
        self.art_entry.delete(0, "end")
        self.art_entry.insert(0, pos.description)
        # Artikel per Datenbank ermitteln, Fallback auf minimale Daten
        found = None
        if pos.ref_id:
            if pos.pos_type == "material":
                found = self.db.material_get(pos.ref_id)
                if found:
                    found["item_type"] = "Material"
                    found["price_per_m2"] = found.get("price_per_m2", 0) or found.get("price", 0)
            else:
                found = self.db.tool_get(pos.ref_id)
                if found:
                    found["item_type"] = "Werkzeug"
                    found["price"] = found.get("price", 0)
                    found["price_per_m2"] = 0
        if not found:
            _t = "Text" if pos.pos_type == "text" else ("Material" if pos.pos_type == "material" else "Werkzeug")
            found = {"id": pos.ref_id or 0, "name": pos.description,
                     "item_type": _t, "price": 0, "price_per_m2": 0, "price_unit": "h"}
        self._selected_article = found
        if pos.pos_type == "material":
            self._show_mat_units()
            ed = pos.extra_data or {}
            if ed.get("length"):
                self.dl_length.delete(0, "end")
                self.dl_length.insert(0, str(ed["length"]))
            if ed.get("width"):
                self.dl_width.delete(0, "end")
                self.dl_width.insert(0, str(ed["width"]))
            self._calc_detail_qm()
        elif pos.pos_type == "tool":
            self._show_tool_units()
            self.dl_time.delete(0, "end")
            self.dl_time.insert(0, str(int(pos.quantity)))
            self.dl_time_unit.set("h" if pos.unit == "Std." else "min")
        else:
            self._hide_units()
        self.art_insert_btn.configure(text="Übernehmen")

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
        for text in ["Netto:", "MwSt:", "Brutto:"]:
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

    # ===================== STATUSBAR =====================
    def _build_statusbar(self):
        bar = ctk.CTkFrame(self, height=24, corner_radius=0, fg_color=("#e0e0e0", "#1a1a1a"))
        bar.pack(fill="x", side="bottom")
        ctk.CTkLabel(bar, text="SondereggerSoftware", font=("Segoe UI", 9),
                     text_color=("#555555", "#888888")).pack(side="left", padx=10)
        ctk.CTkLabel(bar, text=f"v{VERSION}", font=("Segoe UI", 9),
                     text_color=("#555555", "#888888")).pack(side="right", padx=10)

    # ===================== DOKUMENT-LOGIK =====================
    def _new_doc(self):
        self._current_doc_id = None
        self._positions.clear()
        self._refresh_positions()
        self.cust_entry.delete(0, "end")
        self.art_entry.delete(0, "end")
        self.doc_note.delete(0, "end")
        self.discount_var.set("0")
        self.doc_type_var.set("RG")
        self._customer_id = None
        self.cust_btn_edit.configure(state="disabled")
        self._cust_data = []
        self._editing_pos_idx = None
        self._hide_units()
        self._do_hide_cust_dropdown()
        self._do_hide_art_dropdown()

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
            self._set_cust_display(customer)
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
    def _open_doc_overview(self):
        DocSearchDialog(self)

    def _open_customer_mgmt(self):
        CustomerDatabase(self)

    def _open_tool_mgmt(self):
        ToolDatabase(self)

    def _open_material_mgmt(self):
        MaterialDatabase(self)

    def _open_text_mgmt(self):
        TextDatabase(self)

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
            app_path = reg_read("InstallPath", "")
            if app_path:
                app_exe = os.path.join(app_path, "FerdlWorks.exe")
            else:
                app_exe = sys.executable
            if install_and_restart(path, app_exe):
                self.logger.info(f"Update auf v{tag} gestartet, Neustart folgt")
                self.destroy()
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
        self.title("Rechnungen & Lieferscheine")
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
