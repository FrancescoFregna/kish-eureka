"""Interfaccia grafica moderna per l'autoclicker."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, List, Optional, Sequence

from .engine import (
    ActionEngine,
    AutomationAction,
    ClickAction,
    DragAction,
    KeyPressAction,
    MoveAction,
    ScrollAction,
    TypeTextAction,
    WaitAction,
)


class AutomationApp:
    """Applicazione desktop con interfaccia moderna."""

    ACTION_TYPES = (
        "Click",
        "Sposta",
        "Trascina",
        "Tasti",
        "Testo",
        "Attesa",
        "Scroll",
    )

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Eureka Autoclicker")
        self.root.geometry("1000x660")
        self.root.minsize(920, 600)
        self.root.configure(bg="#0f172a")

        self.engine = ActionEngine()
        self.actions: List[AutomationAction] = []

        self.action_type_var = tk.StringVar(value=self.ACTION_TYPES[0])
        self.interval_var = tk.StringVar(value="0.20")
        self.loop_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Sequenza inattiva")

        self._form_frames: Dict[str, tk.Widget] = {}
        self._form_vars: Dict[str, Dict[str, tk.Variable]] = {}
        self._text_widgets: Dict[str, tk.Text] = {}
        self._was_running = False

        self._create_styles()
        self._build_layout()

        self.root.after(200, self._poll_engine)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Creazione dell'interfaccia

    def _create_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:  # pragma: no cover - dipende dall'ambiente
            pass

        base_bg = "#0f172a"
        card_bg = "#1f2937"
        accent = "#6366f1"
        accent_hover = "#4f46e5"
        danger = "#ef4444"
        danger_hover = "#dc2626"
        text_main = "#f8fafc"
        text_muted = "#94a3b8"

        style.configure("Background.TFrame", background=base_bg)
        style.configure("Card.TFrame", background=card_bg)
        style.configure("CardInner.TFrame", background=card_bg)
        style.configure("Card.TLabelframe", background=card_bg, foreground=text_main, borderwidth=0)
        style.configure("Card.TLabelframe.Label", background=card_bg, foreground=text_main, font=("Segoe UI", 12, "bold"))
        style.configure("Title.TLabel", background=base_bg, foreground=text_main, font=("Segoe UI", 22, "bold"))
        style.configure("Subtitle.TLabel", background=base_bg, foreground=text_muted, font=("Segoe UI", 12))
        style.configure("Body.TLabel", background=card_bg, foreground=text_main, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=card_bg, foreground=text_muted, font=("Segoe UI", 10))
        style.configure(
            "Toggle.TCheckbutton",
            background=card_bg,
            foreground=text_main,
            font=("Segoe UI", 10),
        )
        style.map(
            "Toggle.TCheckbutton",
            background=[("active", "#243047")],
            foreground=[("disabled", text_muted)],
        )

        entry_opts = {
            "fieldbackground": "#111827",
            "foreground": text_main,
            "background": card_bg,
            "bordercolor": "#334155",
            "lightcolor": accent,
            "darkcolor": "#0f172a",
            "padding": 6,
        }
        style.configure("Modern.TEntry", **entry_opts)
        style.map(
            "Modern.TEntry",
            fieldbackground=[("focus", "#0b1120")],
            bordercolor=[("focus", accent)],
        )

        style.configure(
            "Accent.TButton",
            background=accent,
            foreground=text_main,
            padding=(16, 10),
            borderwidth=0,
            focusthickness=3,
            focuscolor=accent_hover,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", accent_hover)],
            foreground=[("disabled", "#cbd5f5")],
        )

        style.configure(
            "Ghost.TButton",
            background="#1e293b",
            foreground=text_main,
            padding=(12, 8),
            borderwidth=1,
            focusthickness=2,
            focuscolor=accent,
            font=("Segoe UI", 10),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#334155")],
            foreground=[("disabled", text_muted)],
        )

        style.configure(
            "Danger.TButton",
            background=danger,
            foreground=text_main,
            padding=(16, 10),
            borderwidth=0,
            focusthickness=3,
            focuscolor=danger_hover,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Danger.TButton",
            background=[("active", danger_hover)],
            foreground=[("disabled", "#fca5a5")],
        )

        style.configure(
            "Modern.Treeview",
            background="#111827",
            fieldbackground="#111827",
            foreground=text_main,
            rowheight=32,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Modern.Treeview.Heading",
            background="#1f2937",
            foreground=text_main,
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", accent)],
            foreground=[("selected", text_main)],
        )

        style.configure(
            "Modern.Vertical.TScrollbar",
            background="#334155",
            troughcolor="#1f2937",
            bordercolor="#1f2937",
            arrowcolor=text_main,
        )
        style.map(
            "Modern.Vertical.TScrollbar",
            background=[("active", accent)],
        )

    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, style="Background.TFrame", padding=24)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main, style="Background.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Eureka Autoclicker", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Crea sequenze di input complesse con pochi click.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        content = ttk.Frame(main, style="Background.TFrame")
        content.pack(fill="both", expand=True, pady=(24, 16))
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        self._build_sequence_panel(content)
        self._build_editor_panel(content)
        self._build_controls(main)

    def _build_sequence_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Sequenza di azioni", style="Card.TLabelframe", padding=16)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ("azione", "descrizione")
        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            style="Modern.Treeview",
            height=14,
            selectmode="extended",
        )
        self.tree.heading("azione", text="Azione")
        self.tree.heading("descrizione", text="Dettagli")
        self.tree.column("azione", anchor="center", width=140, stretch=False)
        self.tree.column("descrizione", anchor="w", width=360)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview,
            style="Modern.Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(frame, style="Card.TFrame")
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        for col in range(3):
            buttons.columnconfigure(col, weight=1)

        ttk.Button(
            buttons,
            text="Sposta su",
            command=self._move_up,
            style="Ghost.TButton",
        ).grid(row=0, column=0, padx=4, sticky="ew")
        ttk.Button(
            buttons,
            text="Sposta giù",
            command=self._move_down,
            style="Ghost.TButton",
        ).grid(row=0, column=1, padx=4, sticky="ew")
        ttk.Button(
            buttons,
            text="Rimuovi",
            command=self._remove_selected,
            style="Ghost.TButton",
        ).grid(row=0, column=2, padx=4, sticky="ew")

    def _build_editor_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Nuova azione", style="Card.TLabelframe", padding=16)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Tipologia", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        type_combo = ttk.Combobox(
            frame,
            textvariable=self.action_type_var,
            values=self.ACTION_TYPES,
            state="readonly",
        )
        type_combo.grid(row=0, column=1, sticky="ew")
        type_combo.bind("<<ComboboxSelected>>", lambda _: self._show_form(self.action_type_var.get()))

        self.form_container = ttk.Frame(frame, style="CardInner.TFrame")
        self.form_container.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(16, 12))
        self.form_container.columnconfigure(0, weight=1)
        self.form_container.columnconfigure(1, weight=1)

        self._build_forms()
        self._show_form(self.action_type_var.get())

        ttk.Button(
            frame,
            text="Aggiungi alla sequenza",
            command=self._add_action,
            style="Accent.TButton",
        ).grid(row=2, column=0, columnspan=2, sticky="ew")

    def _build_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Riproduzione", style="Card.TLabelframe", padding=16)
        frame.pack(fill="x")
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text="Intervallo tra azioni (s)", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.interval_var, style="Modern.TEntry", width=10).grid(
            row=0, column=1, padx=(8, 24), sticky="w"
        )
        ttk.Checkbutton(
            frame,
            text="Ripeti in loop",
            variable=self.loop_var,
            style="Toggle.TCheckbutton",
        ).grid(row=0, column=2, sticky="w")

        self.start_btn = ttk.Button(
            frame,
            text="Avvia sequenza",
            command=self._start_sequence,
            style="Accent.TButton",
        )
        self.start_btn.grid(row=1, column=0, columnspan=2, pady=(16, 0), sticky="ew")

        self.stop_btn = ttk.Button(
            frame,
            text="Ferma",
            command=self._stop_sequence,
            style="Danger.TButton",
            state="disabled",
        )
        self.stop_btn.grid(row=1, column=2, padx=(16, 0), pady=(16, 0), sticky="ew")

        ttk.Label(frame, textvariable=self.status_var, style="Muted.TLabel").grid(
            row=1, column=3, sticky="e"
        )

    def _build_forms(self) -> None:
        self._build_click_form()
        self._build_move_form()
        self._build_drag_form()
        self._build_keys_form()
        self._build_text_form()
        self._build_wait_form()
        self._build_scroll_form()

    def _build_click_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {
            "x": tk.StringVar(),
            "y": tk.StringVar(),
            "button": tk.StringVar(value="left"),
            "clicks": tk.StringVar(value="1"),
            "interval": tk.StringVar(value="0.10"),
        }
        self._form_frames["Click"] = frame
        self._form_vars["Click"] = vars

        ttk.Label(frame, text="Coordinate (lascia vuoto per posizione attuale)", style="Body.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Entry(frame, textvariable=vars["x"], style="Modern.TEntry").grid(
            row=1, column=0, sticky="ew", pady=(4, 8), padx=(0, 8)
        )
        ttk.Entry(frame, textvariable=vars["y"], style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 8)
        )
        ttk.Label(frame, text="Pulsante", style="Body.TLabel").grid(row=2, column=0, sticky="w")
        button_combo = ttk.Combobox(
            frame,
            textvariable=vars["button"],
            values=("left", "right", "middle"),
            state="readonly",
        )
        button_combo.grid(row=2, column=1, sticky="ew")
        ttk.Label(frame, text="Ripetizioni", style="Body.TLabel").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=vars["clicks"], style="Modern.TEntry").grid(
            row=3, column=1, sticky="ew", pady=(8, 0)
        )
        ttk.Label(frame, text="Intervallo tra click (s)", style="Body.TLabel").grid(
            row=4, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Entry(frame, textvariable=vars["interval"], style="Modern.TEntry").grid(
            row=4, column=1, sticky="ew", pady=(8, 0)
        )
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_move_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {
            "x": tk.StringVar(),
            "y": tk.StringVar(),
            "duration": tk.StringVar(value="0.0"),
        }
        self._form_frames["Sposta"] = frame
        self._form_vars["Sposta"] = vars

        ttk.Label(frame, text="Coordinate destinazione", style="Body.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Entry(frame, textvariable=vars["x"], style="Modern.TEntry").grid(
            row=1, column=0, sticky="ew", pady=(4, 8), padx=(0, 8)
        )
        ttk.Entry(frame, textvariable=vars["y"], style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 8)
        )
        ttk.Label(frame, text="Durata movimento (s)", style="Body.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["duration"], style="Modern.TEntry").grid(
            row=2, column=1, sticky="ew", pady=(4, 0)
        )
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_drag_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {
            "start_x": tk.StringVar(),
            "start_y": tk.StringVar(),
            "end_x": tk.StringVar(),
            "end_y": tk.StringVar(),
            "duration": tk.StringVar(value="0.4"),
            "button": tk.StringVar(value="left"),
        }
        self._form_frames["Trascina"] = frame
        self._form_vars["Trascina"] = vars

        ttk.Label(frame, text="Punto di partenza (opzionale)", style="Body.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Entry(frame, textvariable=vars["start_x"], style="Modern.TEntry").grid(
            row=1, column=0, sticky="ew", pady=(4, 8), padx=(0, 8)
        )
        ttk.Entry(frame, textvariable=vars["start_y"], style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(4, 8)
        )
        ttk.Label(frame, text="Punto di arrivo", style="Body.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w"
        )
        ttk.Entry(frame, textvariable=vars["end_x"], style="Modern.TEntry").grid(
            row=3, column=0, sticky="ew", pady=(4, 8), padx=(0, 8)
        )
        ttk.Entry(frame, textvariable=vars["end_y"], style="Modern.TEntry").grid(
            row=3, column=1, sticky="ew", pady=(4, 8)
        )
        ttk.Label(frame, text="Durata trascinamento (s)", style="Body.TLabel").grid(
            row=4, column=0, sticky="w"
        )
        ttk.Entry(frame, textvariable=vars["duration"], style="Modern.TEntry").grid(
            row=4, column=1, sticky="ew", pady=(4, 0)
        )
        ttk.Label(frame, text="Pulsante", style="Body.TLabel").grid(row=5, column=0, sticky="w", pady=(8, 0))
        button_combo = ttk.Combobox(
            frame,
            textvariable=vars["button"],
            values=("left", "right", "middle"),
            state="readonly",
        )
        button_combo.grid(row=5, column=1, sticky="ew", pady=(8, 0))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_keys_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {
            "keys": tk.StringVar(),
            "hold": tk.StringVar(value="0.05"),
        }
        self._form_frames["Tasti"] = frame
        self._form_vars["Tasti"] = vars

        ttk.Label(frame, text="Tasti (usa + o , per separare)", style="Body.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(frame, textvariable=vars["keys"], style="Modern.TEntry").grid(
            row=0, column=1, sticky="ew"
        )
        ttk.Label(frame, text="Pausa tra pressioni (s)", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", pady=(12, 0)
        )
        ttk.Entry(frame, textvariable=vars["hold"], style="Modern.TEntry").grid(
            row=1, column=1, sticky="ew", pady=(12, 0)
        )
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_text_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {
            "interval": tk.StringVar(value="0.02"),
        }
        self._form_frames["Testo"] = frame
        self._form_vars["Testo"] = vars

        ttk.Label(frame, text="Testo da digitare", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        text_widget = tk.Text(frame, height=4, wrap="word", bg="#111827", fg="#f8fafc", insertbackground="#f8fafc")
        text_widget.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(4, 8))
        text_widget.configure(highlightthickness=1, highlightbackground="#334155", highlightcolor="#6366f1", relief="flat")
        self._text_widgets["Testo"] = text_widget
        ttk.Label(frame, text="Intervallo tra caratteri (s)", style="Body.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Entry(frame, textvariable=vars["interval"], style="Modern.TEntry").grid(
            row=2, column=1, sticky="ew", pady=(4, 0)
        )
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_wait_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {"seconds": tk.StringVar(value="1.0")}
        self._form_frames["Attesa"] = frame
        self._form_vars["Attesa"] = vars

        ttk.Label(frame, text="Durata attesa (s)", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["seconds"], style="Modern.TEntry").grid(
            row=0, column=1, sticky="ew", pady=(4, 0)
        )
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_scroll_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {
            "amount": tk.StringVar(value="120"),
            "horizontal": tk.BooleanVar(value=False),
        }
        self._form_frames["Scroll"] = frame
        self._form_vars["Scroll"] = vars

        ttk.Label(frame, text="Quantità di scroll", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["amount"], style="Modern.TEntry").grid(
            row=0, column=1, sticky="ew", pady=(4, 0)
        )
        ttk.Checkbutton(
            frame,
            text="Scorri orizzontalmente",
            variable=vars["horizontal"],
            style="Toggle.TCheckbutton",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Gestione azioni

    def _show_form(self, action_type: str) -> None:
        for frame in self._form_frames.values():
            frame.grid_forget()
        frame = self._form_frames[action_type]
        frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    def _add_action(self) -> None:
        action_type = self.action_type_var.get()
        try:
            action = self._create_action(action_type)
        except ValueError as exc:
            messagebox.showerror("Valori non validi", str(exc), parent=self.root)
            return

        self.actions.append(action)
        self._refresh_tree()
        self._select_index(len(self.actions) - 1)

    def _create_action(self, action_type: str) -> AutomationAction:
        builder_map = {
            "Click": self._create_click_action,
            "Sposta": self._create_move_action,
            "Trascina": self._create_drag_action,
            "Tasti": self._create_keys_action,
            "Testo": self._create_text_action,
            "Attesa": self._create_wait_action,
            "Scroll": self._create_scroll_action,
        }
        try:
            builder = builder_map[action_type]
        except KeyError:  # pragma: no cover - impossibile salvo bug
            raise ValueError("Tipo di azione non supportato")
        return builder()

    def _create_click_action(self) -> AutomationAction:
        vars = self._form_vars["Click"]
        x = self._parse_optional_int(vars["x"].get(), "Coordinata X")
        y = self._parse_optional_int(vars["y"].get(), "Coordinata Y")
        button = vars["button"].get().strip().lower() or "left"
        clicks = self._parse_int(vars["clicks"].get(), "Ripetizioni", minimum=1)
        interval = self._parse_float(vars["interval"].get(), "Intervallo", minimum=0.0)
        return ClickAction(x=x, y=y, button=button, clicks=clicks, interval=interval)

    def _create_move_action(self) -> AutomationAction:
        vars = self._form_vars["Sposta"]
        x = self._parse_int(vars["x"].get(), "Coordinata X")
        y = self._parse_int(vars["y"].get(), "Coordinata Y")
        duration = self._parse_float(vars["duration"].get(), "Durata", minimum=0.0)
        return MoveAction(x=x, y=y, duration=duration)

    def _create_drag_action(self) -> AutomationAction:
        vars = self._form_vars["Trascina"]
        start_x = self._parse_optional_int(vars["start_x"].get(), "Start X")
        start_y = self._parse_optional_int(vars["start_y"].get(), "Start Y")
        end_x = self._parse_int(vars["end_x"].get(), "Arrivo X")
        end_y = self._parse_int(vars["end_y"].get(), "Arrivo Y")
        duration = self._parse_float(vars["duration"].get(), "Durata", minimum=0.0)
        button = vars["button"].get().strip().lower() or "left"
        return DragAction(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            duration=duration,
            button=button,
        )

    def _create_keys_action(self) -> AutomationAction:
        vars = self._form_vars["Tasti"]
        raw = vars["keys"].get()
        cleaned = [part.strip() for part in raw.replace("+", ",").split(",") if part.strip()]
        if not cleaned:
            raise ValueError("Inserisci almeno un tasto")
        hold = self._parse_float(vars["hold"].get(), "Pausa", minimum=0.0)
        return KeyPressAction(keys=tuple(cleaned), hold=hold)

    def _create_text_action(self) -> AutomationAction:
        vars = self._form_vars["Testo"]
        widget = self._text_widgets["Testo"]
        text = widget.get("1.0", "end").strip()
        if not text:
            raise ValueError("Inserisci il testo da digitare")
        interval = self._parse_float(vars["interval"].get(), "Intervallo", minimum=0.0)
        return TypeTextAction(text=text, interval=interval)

    def _create_wait_action(self) -> AutomationAction:
        vars = self._form_vars["Attesa"]
        seconds = self._parse_float(vars["seconds"].get(), "Durata", minimum=0.0)
        return WaitAction(seconds=seconds)

    def _create_scroll_action(self) -> AutomationAction:
        vars = self._form_vars["Scroll"]
        amount = self._parse_int(vars["amount"].get(), "Quantità")
        horizontal_var = vars["horizontal"]
        horizontal = bool(horizontal_var.get()) if isinstance(horizontal_var, tk.Variable) else False
        return ScrollAction(amount=amount, horizontal=horizontal)

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, action in enumerate(self.actions):
            self.tree.insert("", "end", iid=str(index), values=(action.label, action.describe()))

    def _select_index(self, index: int) -> None:
        if index < 0:
            return
        iid = str(index)
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        self.tree.see(iid)

    def _selected_indices(self) -> List[int]:
        return sorted(int(iid) for iid in self.tree.selection())

    def _remove_selected(self) -> None:
        indices = self._selected_indices()
        if not indices:
            return
        for index in reversed(indices):
            del self.actions[index]
        self._refresh_tree()

    def _move_up(self) -> None:
        indices = self._selected_indices()
        if not indices or indices[0] == 0:
            return
        for index in indices:
            self.actions[index - 1], self.actions[index] = self.actions[index], self.actions[index - 1]
        self._refresh_tree()
        self._reselect([index - 1 for index in indices])

    def _move_down(self) -> None:
        indices = self._selected_indices()
        if not indices or indices[-1] >= len(self.actions) - 1:
            return
        for index in reversed(indices):
            self.actions[index + 1], self.actions[index] = self.actions[index], self.actions[index + 1]
        self._refresh_tree()
        self._reselect([index + 1 for index in indices])

    def _reselect(self, indices: Sequence[int]) -> None:
        self.tree.selection_remove(*self.tree.selection())
        for index in indices:
            self._select_index(index)

    # ------------------------------------------------------------------
    # Controllo sequenza

    def _start_sequence(self) -> None:
        if self.engine.is_running():
            messagebox.showinfo("Sequenza", "Una sequenza è già in esecuzione", parent=self.root)
            return
        if not self.actions:
            messagebox.showwarning("Sequenza vuota", "Aggiungi almeno un'azione", parent=self.root)
            return

        try:
            interval = self._parse_float(self.interval_var.get(), "Intervallo", minimum=0.0)
        except ValueError as exc:
            messagebox.showerror("Valore non valido", str(exc), parent=self.root)
            return

        loop = bool(self.loop_var.get())
        try:
            self.engine.start(self.actions, interval=interval, loop=loop)
        except Exception as exc:  # pragma: no cover - dipende dall'ambiente
            messagebox.showerror("Impossibile avviare", str(exc), parent=self.root)
            return

        self.status_var.set("Sequenza in esecuzione...")
        self.start_btn.state(["disabled"])
        self.stop_btn.state(["!disabled"])

    def _stop_sequence(self) -> None:
        self.engine.stop()
        self.status_var.set("Sequenza arrestata")
        self.start_btn.state(["!disabled"])
        self.stop_btn.state(["disabled"])

    def _poll_engine(self) -> None:
        running = self.engine.is_running()
        if running != self._was_running:
            self._was_running = running
            if running:
                self.status_var.set("Sequenza in esecuzione...")
                self.start_btn.state(["disabled"])
                self.stop_btn.state(["!disabled"])
            else:
                self.status_var.set("Sequenza completata")
                self.start_btn.state(["!disabled"])
                self.stop_btn.state(["disabled"])
        self.root.after(200, self._poll_engine)

    def _on_close(self) -> None:
        if self.engine.is_running():
            self.engine.stop()
        self.root.destroy()

    # ------------------------------------------------------------------
    # Utility di parsing

    def _parse_optional_int(self, value: str, field: str) -> Optional[int]:
        value = value.strip()
        if not value:
            return None
        return self._parse_int(value, field)

    def _parse_int(self, value: str, field: str, *, minimum: Optional[int] = None) -> int:
        try:
            number = int(value)
        except ValueError as exc:
            raise ValueError(f"{field} deve essere un numero intero") from exc
        if minimum is not None and number < minimum:
            raise ValueError(f"{field} deve essere ≥ {minimum}")
        return number

    def _parse_float(self, value: str, field: str, *, minimum: Optional[float] = None) -> float:
        try:
            number = float(value)
        except ValueError as exc:
            raise ValueError(f"{field} deve essere un numero") from exc
        if minimum is not None and number < minimum:
            raise ValueError(f"{field} deve essere ≥ {minimum}")
        return number

    # ------------------------------------------------------------------
    # Avvio

    def run(self) -> None:
        self.root.mainloop()


def launch_app() -> None:
    """Avvia l'interfaccia grafica dell'autoclicker."""

    root = tk.Tk()
    app = AutomationApp(root)
    app.run()


__all__ = ["launch_app", "AutomationApp"]
