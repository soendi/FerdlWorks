import sys
import os
import subprocess
import customtkinter as ctk
from PIL import Image
from datetime import datetime
from tkinter import messagebox

from lib.logger import setup_logger, get_logger, get_log_path
from lib.registry import reg_write, reg_read, reg_delete_all
from lib.icon import create_icon
from lib.menu import CTkMenuBar
from lib.database import get_db, DB_PATH
from lib.settings_dialog import SettingsDialog
from lib.customer_dialog import CustomerDialog
from lib.tool_dialog import ToolDialog
from lib.material_dialog import MaterialDialog
from lib.pdf_gen import generate_pdf
from lib.email_sender import send_email
from lib.updater import check_for_update, download_installer, install_update
from lib.autostart import autostart_enable, autostart_disable, autostart_is_enabled
from lib.cloud_backup import gdrive_backup, gdrive_authorize, onedrive_backup, onedrive_authorize
from version import VERSION, APP_NAME, COMPANY_NAME

THEME_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "ferdlworks_theme.json")
SCROLLBAR_STYLE = {"width": 3, "corner_radius": 2}


def _format_currency(value):
    return f"{value:.2f}".replace(".", ",")


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
        self._show_version()
        self.logger.info(f"{APP_NAME} v{VERSION} gestartet (Master-Mode: {master_mode})")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ===================== MENU =====================
    def _build_menu(self):
        self.menu_bar = CTkMenuBar(self)
        self.menu_bar.pack(fill="x", padx=0, pady=0)

        datei_items = [
            {"label": "Kunden verwalten...", "key": "Strg+K", "command": self._open_customer_mgmt},
            {"label": "---"},
            {"label": "Beenden", "key": "Strg+Q", "command": self._on_close},
        ]
        werkzeuge_items = [
            {"label": "Werkzeuge verwalten...", "key": "Strg+W", "command": self._open_tool_mgmt},
            {"label": "Materialien verwalten...", "key": "Strg+M", "command": self._open_material_mgmt},
        ]
        einstellungen_items = [
            {"label": "Einstellungen...", "key": "Strg+E", "command": self._open_settings},
            {"label": "---"},
            {"label": "Datensicherung erstellen...", "command": self._backup_data},
            {"label": "Datensicherung wiederherstellen...", "command": self._restore_data},
            {"label": "---"},
            {"label": "Google Drive Backup...", "command": self._cloud_gdrive},
            {"label": "OneDrive Backup...", "command": self._cloud_onedrive},
        ]
        hilfe_items = [
            {"label": "Auf Updates pr\xfcfen...", "key": "Strg+U", "command": self._check_update},
            {"label": "---"},
            {"label": "Logdatei \xf6ffnen", "command": self._open_log},
            {"label": "Logdatei senden...", "command": self._send_log},
            {"label": "---"},
            {"label": "Info...", "command": self._show_info},
            {"label": "---"},
            {"label": "Deinstallieren...", "command": self._uninstall},
        ]
        self.menu_bar.add_menu("  Datei  ", datei_items)
        self.menu_bar.add_menu("  Werkzeuge & Material  ", werkzeuge_items)
        self.menu_bar.add_menu("  Einstellungen  ", einstellungen_items)
        self.menu_bar.add_menu("  Hilfe  ", hilfe_items)

    def _show_version(self):
        self.version_label = ctk.CTkLabel(
            self, text=f"v{VERSION}", font=("Segoe UI", 9),
            text_color=("#666666", "#666666"))
        self.version_label.place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-4)

    def _on_close(self):
        self.logger.info("Anwendung wird beendet")
        self.destroy()
        sys.exit(0)

    # ===================== UI AUFBAU =====================
    def _build_ui(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=("#1a1a1a", "#1a1a1a"))
        self.main_frame.pack(fill="both", expand=True, padx=5, pady=(2, 20))

        # --- Kundenbereich ---
        cust_frame = ctk.CTkFrame(self.main_frame, corner_radius=6)
        cust_frame.pack(fill="x", padx=8, pady=(8, 4))
        ctk.CTkLabel(cust_frame, text="Kunde:", font=("Segoe UI", 12, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(side="left", padx=(10, 5))
        self.cust_search_var = ctk.StringVar()
        self.cust_search_var.trace_add("write", lambda *a: self._search_customers())
        self.cust_entry = ctk.CTkEntry(cust_frame, width=200, placeholder_text="Kunde suchen...",
                                       textvariable=self.cust_search_var)
        self.cust_entry.pack(side="left", padx=5)
        self.cust_combo = ctk.CTkOptionMenu(cust_frame, values=[""], width=300, dynamic_resizing=False)
        self.cust_combo.pack(side="left", padx=5)
        self._cust_data = {}
        ctk.CTkButton(cust_frame, text="Neu", width=50, command=self._new_customer,
                       fg_color="#5c0000", hover_color="#8b0000").pack(side="left", padx=2)
        ctk.CTkButton(cust_frame, text="Edit", width=50, command=self._edit_customer,
                       fg_color="#5c0000", hover_color="#8b0000").pack(side="left", padx=2)
        self._customer_id = None

        # --- Dokument-Typ ---
        dtype_frame = ctk.CTkFrame(cust_frame, fg_color="transparent")
        dtype_frame.pack(side="right", padx=10)
        self.doc_type_var = ctk.StringVar(value="RG")
        ctk.CTkRadioButton(dtype_frame, text="Rechnung", variable=self.doc_type_var, value="RG",
                           font=("Segoe UI", 11)).pack(side="left", padx=5)
        ctk.CTkRadioButton(dtype_frame, text="Lieferschein", variable=self.doc_type_var, value="LS",
                           font=("Segoe UI", 11)).pack(side="left", padx=5)

        # --- Hauptbereich: links Einfügen, rechts Positionen ---
        middle = ctk.CTkFrame(self.main_frame)
        middle.pack(fill="both", expand=True, padx=8, pady=4)
        middle.grid_columnconfigure(0, weight=1)
        middle.grid_columnconfigure(1, weight=2)
        middle.grid_rowconfigure(0, weight=1)

        # --- Linke Seite: Werkzeug/Material Suche ---
        left = ctk.CTkFrame(middle, corner_radius=6)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self._build_left_panel(left)

        # --- Rechte Seite: Positionstabelle ---
        right = ctk.CTkFrame(middle, corner_radius=6)
        right.grid(row=0, column=1, sticky="nsew")
        self._build_right_panel(right)

        # --- Footer: Notiz, Rabatt, Summen, Buttons ---
        bottom = ctk.CTkFrame(self.main_frame, corner_radius=6)
        bottom.pack(fill="x", padx=8, pady=4)
        self._build_footer(bottom)

    def _build_left_panel(self, parent):
        ctk.CTkLabel(parent, text="Werkzeug / Material einf\xfcgen",
                     font=("Segoe UI", 11, "bold"), text_color=("#8b0000", "#8b0000")).pack(padx=8, pady=(8, 2))
        # Such-Tabs
        tab_frame = ctk.CTkFrame(parent, fg_color="transparent")
        tab_frame.pack(fill="x", padx=8, pady=2)
        self._search_type = ctk.StringVar(value="tool")
        ctk.CTkRadioButton(tab_frame, text="Werkzeug", variable=self._search_type, value="tool",
                           command=self._clear_search, font=("Segoe UI", 10)).pack(side="left", padx=5)
        ctk.CTkRadioButton(tab_frame, text="Material", variable=self._search_type, value="material",
                           command=self._clear_search, font=("Segoe UI", 10)).pack(side="left", padx=5)
        self.search_entry = ctk.CTkEntry(parent, placeholder_text="Suchen...")
        self.search_entry.pack(fill="x", padx=8, pady=4)
        self.search_entry.bind("<KeyRelease>", lambda e: self._do_search())
        self.search_listbox = ctk.CTkScrollableFrame(parent, **SCROLLBAR_STYLE)
        self.search_listbox.pack(fill="both", expand=True, padx=8, pady=4)
        self._search_results = []

        # --- Material-Felder (nur bei Material) ---
        self.mat_frame = ctk.CTkFrame(parent, corner_radius=4)
        self.mat_frame.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(self.mat_frame, text="L\xe4nge (cm):", font=("Segoe UI", 10)).grid(row=0, column=0, padx=4, pady=2)
        self.mat_length = ctk.CTkEntry(self.mat_frame, width=70)
        self.mat_length.grid(row=0, column=1, padx=4, pady=2)
        ctk.CTkLabel(self.mat_frame, text="Breite (cm):", font=("Segoe UI", 10)).grid(row=0, column=2, padx=4, pady=2)
        self.mat_width = ctk.CTkEntry(self.mat_frame, width=70)
        self.mat_width.grid(row=0, column=3, padx=4, pady=2)
        ctk.CTkLabel(self.mat_frame, text="Menge:", font=("Segoe UI", 10)).grid(row=1, column=0, padx=4, pady=2)
        self.mat_qty = ctk.CTkEntry(self.mat_frame, width=70)
        self.mat_qty.insert(0, "1")
        self.mat_qty.grid(row=1, column=1, padx=4, pady=2)
        ctk.CTkLabel(self.mat_frame, text="m\xb2:", font=("Segoe UI", 10)).grid(row=1, column=2, padx=4, pady=2)
        self.mat_qm_label = ctk.CTkLabel(self.mat_frame, text="0,00", font=("Segoe UI", 10, "bold"),
                                         text_color=("#8b0000", "#8b0000"))
        self.mat_qm_label.grid(row=1, column=3, padx=4, pady=2)
        # Auto-Berechnung
        self.mat_length.bind("<KeyRelease>", lambda e: self._calc_qm())
        self.mat_width.bind("<KeyRelease>", lambda e: self._calc_qm())
        self.mat_qty.bind("<KeyRelease>", lambda e: self._calc_qm())
        self.mat_frame_visible = True

        ctk.CTkButton(parent, text="Ausgew\xe4hltes einf\xfcgen", command=self._insert_selected,
                       font=("Segoe UI", 10)).pack(padx=8, pady=8, fill="x")

    def _build_right_panel(self, parent):
        ctk.CTkLabel(parent, text="Positionen",
                     font=("Segoe UI", 11, "bold"), text_color=("#8b0000", "#8b0000")).pack(padx=8, pady=(8, 2))
        # Tabellenkopf
        header = ctk.CTkFrame(parent, fg_color="#2a2a2a", height=24, corner_radius=0)
        header.pack(fill="x", padx=8, pady=0)
        for i, txt in enumerate(["Pos.", "Beschreibung", "Menge", "Einheit", "EP", "Gesamt"]):
            w = [30, 240, 55, 55, 70, 80][i]
            ctk.CTkLabel(header, text=txt, font=("Segoe UI", 9, "bold"),
                         width=w).pack(side="left", padx=1)
        self.pos_scroll = ctk.CTkScrollableFrame(parent, **SCROLLBAR_STYLE)
        self.pos_scroll.pack(fill="both", expand=True, padx=8, pady=2)
        self._pos_widgets = []

    def _build_footer(self, parent):
        # Linke Seite: Notiz + Rabatt
        left_f = ctk.CTkFrame(parent, fg_color="transparent")
        left_f.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        ctk.CTkLabel(left_f, text="Notiz:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 5))
        self.doc_note = ctk.CTkEntry(left_f, width=250)
        self.doc_note.pack(side="left", padx=5)
        ctk.CTkLabel(left_f, text="Rabatt %:", font=("Segoe UI", 10)).pack(side="left", padx=(15, 5))
        self.discount_var = ctk.StringVar(value="0")
        self.discount_entry = ctk.CTkEntry(left_f, width=50, textvariable=self.discount_var)
        self.discount_entry.pack(side="left", padx=5)
        self.discount_entry.bind("<KeyRelease>", lambda e: self._recalc_totals())

        # Rechte Seite: Summen
        right_f = ctk.CTkFrame(parent, fg_color="transparent")
        right_f.pack(side="right", padx=8, pady=6)
        self._sum_labels = {}
        for text in ["Netto:", "MwSt.:", "Brutto:"]:
            f = ctk.CTkFrame(right_f, fg_color="transparent")
            f.pack(side="left", padx=10)
            ctk.CTkLabel(f, text=text, font=("Segoe UI", 10)).pack(side="left")
            lbl = ctk.CTkLabel(f, text="0,00 \u20ac", font=("Segoe UI", 10, "bold"),
                               text_color=("#8b0000", "#8b0000"), width=70, anchor="e")
            lbl.pack(side="left", padx=4)
            key = text.replace(":", "").replace(" ", "_").lower()
            self._sum_labels[key] = lbl

        # Action-Buttons
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=8, pady=6)
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
            ctk.CTkButton(btn_frame, text=text, command=cmd, width=80,
                          fg_color=fg, hover_color="#b22222",
                          font=("Segoe UI", 10)).pack(side="left", padx=3)

    # ===================== KUNDEN-LOGIK =====================
    def _search_customers(self):
        query = self.cust_search_var.get()
        customers = self.db.customer_search(query)
        display = {}
        for c in customers:
            name = c.get("company") or f"{c.get('last_name', '')} {c.get('first_name', '')}".strip()
            city = c.get("city", "")
            label = f"{name}  ({city})" if city else name
            display[label] = c["id"]
        self._cust_data = display
        keys = list(display.keys())
        if keys:
            self.cust_combo.configure(values=keys)
            self.cust_combo.set(keys[0])
        else:
            self.cust_combo.configure(values=[""])
            self.cust_combo.set("")

    def _get_selected_customer_id(self):
        label = self.cust_combo.get()
        return self._cust_data.get(label)

    def _new_customer(self):
        dlg = CustomerDialog(self)
        self.wait_window(dlg)
        if dlg.result:
            self._search_customers()

    def _edit_customer(self):
        cid = self._get_selected_customer_id()
        if not cid:
            return
        dlg = CustomerDialog(self, cid)
        self.wait_window(dlg)
        if dlg.result:
            self._search_customers()

    # ===================== SUCHEN & EINFÜGEN =====================
    def _clear_search(self):
        self.search_entry.delete(0, "end")
        self._do_search()

    def _calc_qm(self):
        try:
            length = float(self.mat_length.get().replace(",", ".")) / 100
            width = float(self.mat_width.get().replace(",", ".")) / 100
            qty = float(self.mat_qty.get().replace(",", "."))
            qm = length * width * qty
            self.mat_qm_label.configure(text=f"{qm:.2f}".replace(".", ","))
        except ValueError:
            self.mat_qm_label.configure(text="0,00")

    def _do_search(self):
        for w in self._search_results:
            w.destroy()
        self._search_results.clear()
        query = self.search_entry.get()
        if self._search_type.get() == "tool":
            results = self.db.tool_search(query)
        else:
            results = self.db.material_search(query)
        if not results:
            lbl = ctk.CTkLabel(self.search_listbox, text="Keine Ergebnisse",
                               font=("Segoe UI", 10), text_color="#666666")
            lbl.pack(padx=4, pady=10)
            self._search_results.append(lbl)
            return
        for item in results:
            frame = ctk.CTkFrame(self.search_listbox, corner_radius=3, fg_color="#2a2a2a")
            frame.pack(fill="x", padx=2, pady=1)
            if self._search_type.get() == "tool":
                price_str = f"{item['price']:.2f}" if item['price'] == int(item['price']) else f"{item['price']:.2f}"
                unit = "Std." if item.get("price_unit") == "h" else "Min."
                text = f"{item['name']}  -  {price_str}\u20ac/{unit}"
            else:
                text = f"{item['name']}  -  {item['price_per_m2']:.2f}\u20ac/m\u00b2"
            lbl = ctk.CTkLabel(frame, text=text, font=("Segoe UI", 10), anchor="w")
            lbl.pack(side="left", fill="x", expand=True, padx=6, pady=3)
            btn = ctk.CTkButton(frame, text="+", width=28, height=22,
                                fg_color="#5c0000", hover_color="#8b0000",
                                command=lambda it=item: self._quick_add(it))
            btn.pack(side="right", padx=4, pady=2)
            self._search_results.append(frame)

    def _quick_add(self, item):
        if self._search_type.get() == "tool":
            price = item["price"]
            unit = item.get("price_unit", "h")
            self._positions.append(PositionItem(
                "tool", item["id"], item["name"], 1, unit,
                price, price
            ))
        else:
            try:
                length = float(self.mat_length.get().replace(",", ".")) if self.mat_length.get() else 0
                width = float(self.mat_width.get().replace(",", ".")) if self.mat_width.get() else 0
                qty = float(self.mat_qty.get().replace(",", ".")) if self.mat_qty.get() else 1
            except ValueError:
                length = width = qty = 0
            if length > 0 and width > 0:
                qm = (length / 100) * (width / 100) * qty
                desc = f"{item['name']} ({length:.0f}x{width:.0f}cm x{qty:.0f})"
                total = qm * item["price_per_m2"]
                self._positions.append(PositionItem(
                    "material", item["id"], desc, qm, "qm",
                    item["price_per_m2"], total,
                    {"length": length, "width": width, "qty": qty}
                ))
            else:
                self._positions.append(PositionItem(
                    "material", item["id"], item["name"], 1, "m\u00b2",
                    item["price_per_m2"], item["price_per_m2"]
                ))
        self._refresh_positions()

    def _insert_selected(self):
        # Nur für den Fall, dass der Benutzer "Ausgewähltes einfügen" statt "+" drückt
        pass

    # ===================== POSITIONEN ANZEIGEN =====================
    def _refresh_positions(self):
        for w in self._pos_widgets:
            w.destroy()
        self._pos_widgets.clear()
        for i, pos in enumerate(self._positions):
            frame = ctk.CTkFrame(self.pos_scroll, corner_radius=0, fg_color="#1e1e1e" if i % 2 == 0 else "#222222")
            frame.pack(fill="x", padx=0, pady=0)
            vals = [
                str(i + 1),
                pos.description,
                f"{pos.quantity:.2f}" if pos.quantity != int(pos.quantity) else str(int(pos.quantity)),
                pos.unit,
                f"{pos.price_per_unit:.2f}\u20ac",
                f"{pos.total:.2f}\u20ac",
            ]
            for j, txt in enumerate(vals):
                w = [30, 240, 55, 55, 70, 80][j]
                align = "w" if j in [0, 1] else "e"
                lbl = ctk.CTkLabel(frame, text=txt, font=("Segoe UI", 9), width=w, anchor=align)
                lbl.pack(side="left", padx=1)
            # Löschen-Button pro Position
            del_btn = ctk.CTkButton(frame, text="X", width=22, height=18,
                                    fg_color="#5c0000", hover_color="#b22222",
                                    font=("Segoe UI", 8),
                                    command=lambda idx=i: self._remove_position(idx))
            del_btn.pack(side="right", padx=4)
            self._pos_widgets.append(frame)
        self._recalc_totals()

    def _remove_position(self, idx):
        if 0 <= idx < len(self._positions):
            self._positions.pop(idx)
            self._refresh_positions()

    # ===================== SUMMEN BERECHNEN =====================
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

    # ===================== DOKUMENT-SPEICHERUNG =====================
    def _new_doc(self):
        self._current_doc_id = None
        self._positions.clear()
        self._refresh_positions()
        self.cust_search_var.set("")
        self.search_entry.delete(0, "end")
        self.doc_note.delete(0, "end")
        self.discount_var.set("0")
        self.doc_type_var.set("RG")
        self._cust_data = {}

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
        # Kunde
        customer = doc.get("customer")
        if customer:
            self.cust_search_var.set(customer.get("company") or f"{customer.get('last_name', '')}")
        # Positionen
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

    # ===================== PDF =====================
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

    # ===================== E-MAIL =====================
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

    # ===================== DRUCKEN =====================
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

    def _open_customer_mgmt(self):
        MgmtDialog(self, "customer")

    def _open_tool_mgmt(self):
        MgmtDialog(self, "tool")

    def _open_material_mgmt(self):
        MgmtDialog(self, "material")

    def _open_log(self):
        log_path = get_log_path()
        try:
            os.startfile(log_path)
            self.logger.info(f"Logdatei geöffnet: {log_path}")
        except Exception as ex:
            self.logger.error(f"Konnte Logdatei nicht öffnen: {ex}")

    def _send_log(self):
        log_path = get_log_path()
        recipient = "support@sonderegger-software.de"
        success, msg = send_email(recipient, f"{APP_NAME} Logdatei",
                                  f"Anbei die Logdatei von {APP_NAME} v{VERSION}", log_path)
        if success:
            messagebox.showinfo("E-Mail", msg)
        else:
            messagebox.showerror("Fehler", msg)

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
        info_win = ctk.CTkToplevel(self)
        info_win.title("Info")
        info_win.geometry("350x200")
        info_win.resizable(False, False)
        info_win.transient(self)
        info_win.grab_set()
        ctk.CTkLabel(info_win, text=APP_NAME, font=("Segoe UI", 18, "bold"),
                     text_color=("#8b0000", "#8b0000")).pack(pady=(20, 5))
        ctk.CTkLabel(info_win, text=f"Version {VERSION}", font=("Segoe UI", 12)).pack()
        ctk.CTkLabel(info_win, text=COMPANY_NAME, font=("Segoe UI", 11),
                     text_color="#888888").pack(pady=(10, 0))
        ctk.CTkLabel(info_win, text="© 2026 Sonderegger Software", font=("Segoe UI", 10),
                     text_color="#666666").pack(pady=(5, 0))


# ===================== VERWALTUNGS-DIALOGE =====================
class MgmtDialog(ctk.CTkToplevel):
    def __init__(self, master, mgmt_type):
        super().__init__(master)
        self.db = get_db()
        self.mgmt_type = mgmt_type
        titles = {"customer": "Kunden verwalten", "tool": "Werkzeuge verwalten", "material": "Materialien verwalten"}
        self.title(titles.get(mgmt_type, "Verwaltung"))
        self.geometry("750x500")
        self.transient(master)
        self.grab_set()
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=10)
        self.search_entry = ctk.CTkEntry(top, placeholder_text="Suchen...", width=300)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self._load_data())
        ctk.CTkButton(top, text="Neu", command=self._new_item, width=60).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Bearbeiten", command=self._edit_item, width=100).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Löschen", command=self._delete_item, width=80,
                       fg_color="#5c0000", hover_color="#8b0000").pack(side="left", padx=5)
        ctk.CTkButton(top, text="Schließen", command=self.destroy, width=80).pack(side="right", padx=5)
        self.scroll = ctk.CTkScrollableFrame(self, width=730, height=380)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._item_buttons = []

    def _load_data(self):
        for w in self._item_buttons:
            w.destroy()
        self._item_buttons.clear()
        query = self.search_entry.get()
        if self.mgmt_type == "customer":
            data = self.db.customer_search(query)
            for item in data:
                name = item.get("company") or f"{item.get('last_name', '')} {item.get('first_name', '')}".strip()
                city = item.get("city", "")
                text = f"{name}  ({item.get('street', '')}, {item.get('zip', '')} {city})"
                btn = ctk.CTkButton(self.scroll, text=text, anchor="w", fg_color="transparent",
                                     hover_color="#2a2a2a", command=lambda it=item: self._select(it))
                btn.pack(fill="x", padx=2, pady=1)
                self._item_buttons.append(btn)
        elif self.mgmt_type == "tool":
            data = self.db.tool_search(query)
            for item in data:
                price_str = f"{item['price']:.2f}".replace(".", ",")
                unit = "Std." if item.get("price_unit") == "h" else "Min."
                text = f"{item['name']}  -  {price_str}\u20ac/{unit}"
                btn = ctk.CTkButton(self.scroll, text=text, anchor="w", fg_color="transparent",
                                     hover_color="#2a2a2a", command=lambda it=item: self._select(it))
                btn.pack(fill="x", padx=2, pady=1)
                self._item_buttons.append(btn)
        elif self.mgmt_type == "material":
            data = self.db.material_search(query)
            for item in data:
                price_str = f"{item['price_per_m2']:.2f}".replace(".", ",")
                text = f"{item['name']}  -  {price_str}\u20ac/m\u00b2"
                btn = ctk.CTkButton(self.scroll, text=text, anchor="w", fg_color="transparent",
                                     hover_color="#2a2a2a", command=lambda it=item: self._select(it))
                btn.pack(fill="x", padx=2, pady=1)
                self._item_buttons.append(btn)
        self._selected = None

    def _select(self, item):
        self._selected = item

    def _new_item(self):
        if self.mgmt_type == "customer":
            dlg = CustomerDialog(self)
        elif self.mgmt_type == "tool":
            dlg = ToolDialog(self)
        else:
            dlg = MaterialDialog(self)
        self.wait_window(dlg)
        if dlg and dlg.result:
            self._load_data()

    def _edit_item(self):
        if not self._selected:
            return
        item_id = self._selected["id"]
        if self.mgmt_type == "customer":
            dlg = CustomerDialog(self, item_id)
        elif self.mgmt_type == "tool":
            dlg = ToolDialog(self, item_id)
        else:
            dlg = MaterialDialog(self, item_id)
        self.wait_window(dlg)
        if dlg and dlg.result:
            self._load_data()

    def _delete_item(self):
        if not self._selected:
            return
        if messagebox.askyesno("Löschen", "Wirklich löschen?"):
            item_id = self._selected["id"]
            if self.mgmt_type == "customer":
                self.db.customer_delete(item_id)
            elif self.mgmt_type == "tool":
                self.db.tool_delete(item_id)
            else:
                self.db.material_delete(item_id)
            self._selected = None
            self._load_data()


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
        opt = ctk.CTkOptionMenu(top, values=["Alle", "RG", "LS"], variable=self.type_var, command=lambda v: self._load_data(), width=70)
        opt.pack(side="left", padx=5)
        ctk.CTkButton(top, text="Öffnen", command=self._open_selected, width=80).pack(side="right", padx=5)
        ctk.CTkButton(top, text="Schließen", command=self.destroy, width=80).pack(side="right", padx=5)
        self.scroll = ctk.CTkScrollableFrame(self, width=680, height=350)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._items = []

    def _load_data(self):
        for w in self._items:
            w.destroy()
        self._items.clear()
        type_filter = {"Alle": None, "RG": "RG", "LS": "LS"}.get(self.type_var.get(), None)
        query = self.search_entry.get()
        docs = self.db.doc_search(type_filter, query)
        for doc in docs:
            cname = doc.get("customer_name", "")
            dtype = "RG" if doc["doc_type"] == "RG" else "LS"
            text = f"{dtype} {doc['doc_number']}  |  {doc['date']}  |  {cname}  |  {doc.get('total_gross', 0):.2f}\u20ac"
            btn = ctk.CTkButton(self.scroll, text=text, anchor="w", fg_color="transparent",
                                 hover_color="#2a2a2a", command=lambda d=doc: self._open_doc(d))
            btn.pack(fill="x", padx=2, pady=1)
            self._items.append(btn)

    def _open_selected(self):
        pass

    def _open_doc(self, doc):
        self.app._load_doc(doc["id"])
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
    from lib.database import get_db
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
