import customtkinter as ctk


class CTkMenuBar(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, height=28, **kwargs)
        self.pack_propagate(False)
        self.grid_propagate(False)
        self._items = {}
        self._active_menu = None
        self._dropdown = None
        self._master = master

    def add_menu(self, label: str, items: list):
        btn = ctk.CTkButton(
            self,
            text=label,
            fg_color="transparent",
            text_color=("#e0e0e0", "#e0e0e0"),
            hover_color=("#3a0000", "#3a0000"),
            height=28,
            corner_radius=0,
            font=("Segoe UI", 11),
            command=lambda l=label, it=items: self._toggle_menu(l, it),
        )
        btn.pack(side="left", padx=0, pady=0)
        self._items[label] = (btn, items)

    def _toggle_menu(self, label, items):
        if self._dropdown and self._dropdown.winfo_exists():
            self._hide_dropdown()
            if self._active_menu == label:
                return
        self._active_menu = label
        self._show_dropdown(label, items)

    def _show_dropdown(self, label, items):
        btn, _ = self._items[label]
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        self._dropdown = DropdownMenu(self._master, items, x, y)
        self._dropdown.bind("<Leave>", self._on_mouse_leave)
        self._master.bind("<Configure>", self._on_window_move, add="+")

    def _on_mouse_leave(self, event):
        if not self._dropdown or not self._dropdown.winfo_exists():
            return
        dx = event.x_root - self._dropdown.winfo_rootx()
        dy = event.y_root - self._dropdown.winfo_rooty()
        if dx < -50 or dx > self._dropdown.winfo_width() + 50 or dy < -50 or dy > self._dropdown.winfo_height() + 50:
            self._hide_dropdown()

    def _on_window_move(self, event):
        self._hide_dropdown()

    def _on_mouse_click(self, event):
        self._hide_dropdown()

    def _hide_dropdown(self):
        if self._dropdown:
            try:
                self._dropdown.unbind("<Leave>")
                self._dropdown.destroy()
            except Exception:
                pass
            self._dropdown = None
        self._active_menu = None
        try:
            self._master.unbind("<Configure>")
        except Exception:
            pass


class DropdownMenu(ctk.CTkFrame):
    def __init__(self, master, items, x, y):
        super().__init__(
            master,
            fg_color=("#2a2a2a", "#2a2a2a"),
            border_color=("#8b0000", "#8b0000"),
            border_width=1,
            corner_radius=4,
        )
        self._items = []
        for item in items:
            if item == "---":
                sep = ctk.CTkFrame(self, height=1, fg_color=("#5c0000", "#5c0000"))
                sep.pack(fill="x", padx=10, pady=3)
                continue
            label = item.get("label", "")
            cmd = item.get("command")
            key = item.get("key", "")
            disabled = item.get("disabled", False)
            text = f"{label}      {key}" if key else label
            btn = ctk.CTkButton(
                self,
                text=text,
                fg_color="transparent",
                text_color=("#e0e0e0", "#e0e0e0"),
                hover_color=("#8b0000", "#8b0000"),
                anchor="w",
                height=26,
                corner_radius=2,
                font=("Segoe UI", 11),
                command=cmd if cmd and not disabled else None,
                state="normal" if not disabled else "disabled",
            )
            btn.pack(fill="x", padx=4, pady=1)
            self._items.append(btn)
        self.place(x=0, y=0)
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        rx = x if x + w <= sw else sw - w - 10
        ry = y if y + h <= sh else y - h - 28
        self.place(x=rx, y=ry)
        self.lift()
