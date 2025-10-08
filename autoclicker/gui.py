"""Interfaccia grafica moderna e animata per l'autoclicker."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from typing import Dict, Iterable, List, Optional, Sequence

from .engine import (
    ActionEngine,
    AutomationAction,
    ClickAction,
    DragAction,
    InputToolkit,
    KeyPressAction,
    MoveAction,
    ScrollAction,
    TypeTextAction,
    WaitAction,
    deserialize_actions,
    serialize_actions,
)


class RippleOverlay:
    """Gestore di animazioni "ripple" per i pulsanti della GUI."""

    # Colori base per le varie famiglie di pulsanti; vengono usati per disegnare
    # la sovrapposizione temporanea senza alterare la palette originale.
    STYLE_COLORS = {
        "Accent.TButton": ("#6366f1", "#f8fafc"),
        "Ghost.TButton": ("#1e293b", "#e2e8f0"),
        "Danger.TButton": ("#ef4444", "#fee2e2"),
    }

    def __init__(self, root: tk.Misc, *, fallback_bg: str, fallback_fg: str) -> None:
        self.root = root
        self.fallback_bg = fallback_bg
        self.fallback_fg = fallback_fg
        self._style = ttk.Style()

    def attach(self, widget: ttk.Widget, style: str) -> None:
        """Collega l'animazione al widget, preservando eventuali binding esistenti."""

        widget.bind(
            "<Button-1>",
            lambda event, btn=widget, sty=style: self._spawn_ripple(btn, sty, event),
            add="+",
        )

    # ------------------------------------------------------------------
    # Effetti visivi

    def _spawn_ripple(self, widget: ttk.Widget, style: str, event: tk.Event) -> None:
        """Crea una piccola animazione circolare centrata sul punto di click."""

        # Non animiamo se il pulsante è disabilitato: la UI comunicherebbe uno
        # stato attivo quando in realtà non lo è.
        if "disabled" in widget.state():  # type: ignore[attr-defined]
            return

        widget.update_idletasks()
        width = widget.winfo_width()
        height = widget.winfo_height()
        if width <= 0 or height <= 0:
            return

        origin_x = widget.winfo_rootx() - self.root.winfo_rootx()
        origin_y = widget.winfo_rooty() - self.root.winfo_rooty()

        bg_color, fg_color = self._resolve_colors(widget, style)
        font = self._resolve_font(widget, style)

        canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            highlightthickness=0,
            bd=0,
            bg=bg_color,
        )
        canvas.place(x=origin_x, y=origin_y)
        canvas.lift()

        # Riproduciamo testo e (se presente) underline per mantenere la
        # leggibilità dell'etichetta durante l'effetto.
        canvas.create_rectangle(0, 0, width, height, outline="", fill=bg_color)
        canvas.create_text(
            width / 2,
            height / 2,
            text=widget.cget("text"),
            fill=fg_color,
            font=font,
        )

        max_radius = math.hypot(width, height)
        ripple = canvas.create_oval(
            event.x,
            event.y,
            event.x,
            event.y,
            outline=fg_color,
            width=2,
        )

        steps = 12
        duration = 160  # ms complessivi dell'effetto

        def animate(step: int = 0) -> None:
            progress = step / steps
            radius = (0.2 + 0.8 * progress) * max_radius
            canvas.coords(
                ripple,
                event.x - radius,
                event.y - radius,
                event.x + radius,
                event.y + radius,
            )

            # L'outline sfuma progressivamente verso il colore di sfondo.
            mix = self._mix_color(fg_color, bg_color, progress)
            canvas.itemconfigure(ripple, outline=mix)

            if step < steps:
                canvas.after(int(duration / steps), animate, step + 1)
            else:
                canvas.destroy()

        animate()

    def _resolve_colors(self, widget: ttk.Widget, style: str) -> tuple[str, str]:
        """Restituisce il colore di sfondo/testo da usare per il ripple."""

        if style in self.STYLE_COLORS:
            return self.STYLE_COLORS[style]

        bg = self._style.lookup(style, "background") or widget.winfo_toplevel().cget("bg")
        fg = self._style.lookup(style, "foreground") or self.fallback_fg
        return bg or self.fallback_bg, fg

    def _resolve_font(self, widget: ttk.Widget, style: str) -> tkfont.Font:
        """Estrae il font associato allo stile, con fallback su quello di default."""

        font_name = self._style.lookup(style, "font")
        if font_name:
            try:
                return tkfont.nametofont(font_name)
            except tk.TclError:
                pass
        try:
            return tkfont.nametofont(widget.cget("font"))  # type: ignore[arg-type]
        except tk.TclError:
            return tkfont.nametofont("TkDefaultFont")

    @staticmethod
    def _mix_color(foreground: str, background: str, alpha: float) -> str:
        """Miscela due colori espressi in HEX, restituendo un nuovo HEX."""

        def _hex_to_rgb(color: str) -> tuple[int, int, int]:
            color = color.lstrip("#")
            return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)

        def _rgb_to_hex(rgb: Iterable[int]) -> str:
            return "#" + "".join(f"{max(0, min(255, c)):02x}" for c in rgb)

        fg = _hex_to_rgb(foreground)
        bg = _hex_to_rgb(background)
        mix = [int(f * (1 - alpha) + b * alpha) for f, b in zip(fg, bg)]
        return _rgb_to_hex(mix)


class AutomationApp:
    """Applicazione desktop con interfaccia moderna, scorrevole e animata."""

    BASE_BG = "#050b1e"
    CARD_BG = "#0f172a"
    ACCENT = "#6366f1"
    ACCENT_SOFT = "#4f46e5"
    DANGER = "#ef4444"
    DANGER_SOFT = "#dc2626"
    TEXT_MAIN = "#f8fafc"
    TEXT_MUTED = "#9ca3af"

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
        self.root.configure(bg=self.BASE_BG)
        self.root.geometry("1120x720")
        self.root.minsize(960, 640)

        self.engine = ActionEngine()
        self.actions: List[AutomationAction] = []

        # Variabili associate ai controlli globali della sequenza.
        self.action_type_var = tk.StringVar(value=self.ACTION_TYPES[0])
        self.interval_var = tk.StringVar(value="0.20")
        self.loop_var = tk.BooleanVar(value=False)
        self.countdown_var = tk.StringVar(value="0.0")
        self.status_var = tk.StringVar(value="Sequenza inattiva")

        # Cache dei form dinamici per generare le azioni.
        self._form_frames: Dict[str, tk.Widget] = {}
        self._form_vars: Dict[str, Dict[str, tk.Variable]] = {}
        self._text_widgets: Dict[str, tk.Text] = {}
        self._last_sequence_path: Optional[str] = None

        self._was_running = False
        self._was_waiting = False
        self._hero_phase = 0.0

        try:
            self._capture_toolkit = InputToolkit()
        except Exception:  # pragma: no cover - dipende dai moduli disponibili
            self._capture_toolkit = None

        self._overlay = RippleOverlay(
            self.root,
            fallback_bg=self.ACCENT,
            fallback_fg=self.TEXT_MAIN,
        )
        self._create_styles()
        self._build_layout()

        self.root.after(60, self._animate_header_gradient)
        self.root.after(200, self._poll_engine)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Creazione dell'interfaccia

    def _create_styles(self) -> None:
        """Definisce la palette e le personalizzazioni ttk."""

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:  # pragma: no cover - dipende dalla piattaforma
            pass

        style.configure("Background.TFrame", background=self.BASE_BG)
        style.configure("Card.TFrame", background=self.CARD_BG)
        style.configure("CardInner.TFrame", background=self.CARD_BG)
        style.configure("Card.TLabelframe", background=self.CARD_BG, foreground=self.TEXT_MAIN, borderwidth=0)
        style.configure(
            "Card.TLabelframe.Label",
            background=self.CARD_BG,
            foreground=self.TEXT_MAIN,
            font=("Segoe UI", 12, "bold"),
        )
        style.configure("Title.TLabel", background=self.CARD_BG, foreground=self.TEXT_MAIN, font=("Segoe UI", 26, "bold"))
        style.configure("HeroSubtitle.TLabel", background=self.CARD_BG, foreground="#cbd5f5", font=("Segoe UI", 12))
        style.configure("Subtitle.TLabel", background=self.BASE_BG, foreground=self.TEXT_MUTED, font=("Segoe UI", 12))
        style.configure("Body.TLabel", background=self.CARD_BG, foreground=self.TEXT_MAIN, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.CARD_BG, foreground=self.TEXT_MUTED, font=("Segoe UI", 10))
        style.configure("Status.TLabel", background=self.BASE_BG, foreground=self.TEXT_MAIN, font=("Segoe UI", 11, "bold"))

        entry_options = {
            "fieldbackground": "#111827",
            "foreground": self.TEXT_MAIN,
            "background": self.CARD_BG,
            "bordercolor": "#334155",
            "lightcolor": self.ACCENT,
            "darkcolor": self.BASE_BG,
            "padding": 6,
        }
        style.configure("Modern.TEntry", **entry_options)
        style.map(
            "Modern.TEntry",
            fieldbackground=[("focus", "#0b1120")],
            bordercolor=[("focus", self.ACCENT)],
        )

        style.configure(
            "Accent.TButton",
            background=self.ACCENT,
            foreground=self.TEXT_MAIN,
            padding=(18, 12),
            borderwidth=0,
            focusthickness=3,
            focuscolor=self.ACCENT_SOFT,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.ACCENT_SOFT)],
            foreground=[("disabled", "#cbd5f5")],
        )

        style.configure(
            "Ghost.TButton",
            background="#1e293b",
            foreground=self.TEXT_MAIN,
            padding=(14, 10),
            borderwidth=0,
            focusthickness=2,
            focuscolor=self.ACCENT,
            font=("Segoe UI", 10),
        )
        style.map(
            "Ghost.TButton",
            background=[("active", "#273448")],
            foreground=[("disabled", self.TEXT_MUTED)],
        )

        style.configure(
            "Danger.TButton",
            background=self.DANGER,
            foreground=self.TEXT_MAIN,
            padding=(18, 12),
            borderwidth=0,
            focusthickness=3,
            focuscolor=self.DANGER_SOFT,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Danger.TButton",
            background=[("active", self.DANGER_SOFT)],
            foreground=[("disabled", "#fecaca")],
        )

        style.configure(
            "Toggle.TCheckbutton",
            background=self.CARD_BG,
            foreground=self.TEXT_MAIN,
            font=("Segoe UI", 10),
        )
        style.map(
            "Toggle.TCheckbutton",
            background=[("active", "#1f2937")],
            foreground=[("disabled", self.TEXT_MUTED)],
        )

        style.configure(
            "Modern.Treeview",
            background="#111827",
            fieldbackground="#111827",
            foreground=self.TEXT_MAIN,
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Modern.Treeview.Heading",
            background="#1f2937",
            foreground=self.TEXT_MAIN,
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Modern.Treeview",
            background=[("selected", self.ACCENT)],
            foreground=[("selected", self.TEXT_MAIN)],
        )

        style.configure(
            "Modern.Vertical.TScrollbar",
            background="#334155",
            troughcolor=self.CARD_BG,
            bordercolor=self.CARD_BG,
            arrowcolor=self.TEXT_MAIN,
        )
        style.map("Modern.Vertical.TScrollbar", background=[("active", self.ACCENT_SOFT)])

    def _build_layout(self) -> None:
        """Crea il layout principale con area scorrevole e pannelli."""

        container = ttk.Frame(self.root, style="Background.TFrame")
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            container,
            bg=self.BASE_BG,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=self.canvas.yview,
            style="Modern.Vertical.TScrollbar",
        )
        scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.content = ttk.Frame(self.canvas, style="Background.TFrame")
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")

        self.content.bind("<Configure>", self._update_scroll_region)
        self.canvas.bind("<Configure>", self._stretch_content)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel, add="+")

        self.content.columnconfigure(0, weight=1)

        self._build_header(self.content)

        main_body = ttk.Frame(self.content, style="Background.TFrame")
        main_body.grid(row=1, column=0, sticky="nsew", pady=(24, 24))
        main_body.columnconfigure(0, weight=3)
        main_body.columnconfigure(1, weight=2)

        self._build_sequence_panel(main_body)
        self._build_editor_panel(main_body)
        self._build_controls(self.content)

    def _build_header(self, parent: ttk.Frame) -> None:
        """Crea l'introduzione superiore con animazione a gradiente."""

        hero_wrapper = ttk.Frame(parent, style="Background.TFrame", padding=(0, 32, 0, 0))
        hero_wrapper.grid(row=0, column=0, sticky="ew")
        hero_wrapper.columnconfigure(0, weight=1)

        hero = ttk.Frame(hero_wrapper, style="Card.TFrame")
        hero.grid(row=0, column=0, sticky="ew")
        hero.columnconfigure(0, weight=1)

        self.hero_canvas = tk.Canvas(hero, bg=self.CARD_BG, highlightthickness=0, bd=0)
        self.hero_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        inner = ttk.Frame(hero, style="CardInner.TFrame", padding=32)
        inner.grid(row=0, column=0, sticky="nsew")
        inner.columnconfigure(0, weight=1)

        ttk.Label(inner, text="Eureka Autoclicker", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            inner,
            text="Automazioni precise di click, trascinamenti e scorciatoie da tastiera,"
            " orchestrate in sequenze riutilizzabili.",
            style="HeroSubtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))

        ideas = ttk.Frame(inner, style="CardInner.TFrame")
        ideas.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        ideas.columnconfigure(0, weight=1)

        ttk.Label(
            ideas,
            text="Novità rapide:",
            style="Muted.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            ideas,
            text="• Countdown programmabile • Libreria sequenze JSON • Cattura coordinate live",
            style="Body.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

    def _build_sequence_panel(self, parent: ttk.Frame) -> None:
        """Crea il pannello con la lista delle azioni correnti."""

        frame = ttk.LabelFrame(parent, text="Sequenza di azioni", style="Card.TLabelframe", padding=20)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 24))
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
        self.tree.column("azione", anchor="center", width=150, stretch=False)
        self.tree.column("descrizione", anchor="w", width=420)
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview,
            style="Modern.Vertical.TScrollbar",
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(frame, style="CardInner.TFrame")
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        for col in range(3):
            buttons.columnconfigure(col, weight=1)
        buttons.rowconfigure(0, weight=1)
        buttons.rowconfigure(1, weight=1)

        self._button(buttons, "Sposta su", self._move_up, "Ghost.TButton").grid(row=0, column=0, padx=6, sticky="ew")
        self._button(buttons, "Sposta giù", self._move_down, "Ghost.TButton").grid(row=0, column=1, padx=6, sticky="ew")
        self._button(buttons, "Rimuovi", self._remove_selected, "Ghost.TButton").grid(row=0, column=2, padx=6, sticky="ew")
        self._button(buttons, "Duplica", self._duplicate_selected, "Ghost.TButton").grid(row=1, column=0, padx=6, pady=(12, 0), sticky="ew")
        self._button(buttons, "Esporta JSON", self._export_sequence, "Ghost.TButton").grid(row=1, column=1, padx=6, pady=(12, 0), sticky="ew")
        self._button(buttons, "Importa JSON", self._import_sequence, "Ghost.TButton").grid(row=1, column=2, padx=6, pady=(12, 0), sticky="ew")

    def _build_editor_panel(self, parent: ttk.Frame) -> None:
        """Crea il pannello laterale per configurare nuove azioni."""

        frame = ttk.LabelFrame(parent, text="Editor azioni", style="Card.TLabelframe", padding=20)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Tipo di azione", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        combo = ttk.Combobox(frame, values=self.ACTION_TYPES, textvariable=self.action_type_var, state="readonly")
        combo.grid(row=0, column=1, sticky="ew")
        combo.bind("<<ComboboxSelected>>", lambda _event: self._show_form(self.action_type_var.get()))

        self.form_container = ttk.Frame(frame, style="CardInner.TFrame")
        self.form_container.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(16, 16))
        self.form_container.columnconfigure(0, weight=1)
        self.form_container.columnconfigure(1, weight=1)

        self._build_click_form()
        self._build_move_form()
        self._build_drag_form()
        self._build_keys_form()
        self._build_text_form()
        self._build_wait_form()
        self._build_scroll_form()
        self._show_form(self.ACTION_TYPES[0])

        self._button(frame, "Aggiungi azione", self._add_action, "Accent.TButton").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
        )

    def _build_controls(self, parent: ttk.Frame) -> None:
        """Crea i controlli globali per intervallo, ripetizioni e riproduzione."""

        controls = ttk.Frame(parent, style="Background.TFrame")
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 32))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(2, weight=1)

        card = ttk.Frame(controls, style="Card.TFrame", padding=24)
        card.grid(row=0, column=0, columnspan=3, sticky="ew")
        card.columnconfigure(0, weight=1)
        card.columnconfigure(1, weight=1)
        card.columnconfigure(2, weight=1)
        card.columnconfigure(3, weight=1)

        ttk.Label(card, text="Intervallo tra azioni (s)", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(card, textvariable=self.interval_var, style="Modern.TEntry").grid(row=1, column=0, sticky="ew", pady=(6, 0))

        ttk.Label(card, text="Countdown iniziale (s)", style="Body.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Entry(card, textvariable=self.countdown_var, style="Modern.TEntry").grid(row=1, column=1, sticky="ew", pady=(6, 0))

        loop_toggle = ttk.Checkbutton(card, text="Ripeti sequenza", variable=self.loop_var, style="Toggle.TCheckbutton")
        loop_toggle.grid(row=0, column=2, sticky="w", padx=(12, 0))

        ttk.Label(card, text="Stato", style="Body.TLabel").grid(row=0, column=3, sticky="w")
        ttk.Label(card, textvariable=self.status_var, style="Muted.TLabel").grid(row=1, column=3, sticky="w", pady=(6, 0))

        actions_row = ttk.Frame(card, style="CardInner.TFrame")
        actions_row.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(22, 0))
        actions_row.columnconfigure(0, weight=1)
        actions_row.columnconfigure(1, weight=1)

        self.start_btn = self._button(actions_row, "Avvia sequenza", self._start_sequence, "Accent.TButton")
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        self.stop_btn = self._button(actions_row, "Ferma", self._stop_sequence, "Danger.TButton")
        self.stop_btn.grid(row=0, column=1, sticky="ew")
        self.stop_btn.state(["disabled"])

    # ------------------------------------------------------------------
    # Costruzione dinamica dei form

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

        ttk.Label(frame, text="Coordinata X", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["x"], style="Modern.TEntry").grid(row=0, column=1, sticky="ew")
        ttk.Label(frame, text="Coordinata Y", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=vars["y"], style="Modern.TEntry").grid(row=1, column=1, sticky="ew", pady=(8, 0))
        self._button(
            frame,
            "Cattura coordinate",
            lambda: self._capture_coordinates(vars["x"], vars["y"], label="Click"),
            "Ghost.TButton",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        ttk.Label(frame, text="Numero di click", style="Body.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=vars["clicks"], style="Modern.TEntry").grid(row=3, column=1, sticky="ew", pady=(12, 0))

        ttk.Label(frame, text="Intervallo tra click (s)", style="Body.TLabel").grid(row=4, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=vars["interval"], style="Modern.TEntry").grid(row=4, column=1, sticky="ew", pady=(12, 0))

        ttk.Label(frame, text="Pulsante", style="Body.TLabel").grid(row=5, column=0, sticky="w", pady=(12, 0))
        combo = ttk.Combobox(frame, textvariable=vars["button"], values=("left", "right", "middle"), state="readonly")
        combo.grid(row=5, column=1, sticky="ew", pady=(12, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_move_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {"x": tk.StringVar(), "y": tk.StringVar(), "duration": tk.StringVar(value="0.20")}
        self._form_frames["Sposta"] = frame
        self._form_vars["Sposta"] = vars

        ttk.Label(frame, text="Arrivo X", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["x"], style="Modern.TEntry").grid(row=0, column=1, sticky="ew")
        ttk.Label(frame, text="Arrivo Y", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=vars["y"], style="Modern.TEntry").grid(row=1, column=1, sticky="ew", pady=(8, 0))
        self._button(
            frame,
            "Cattura arrivo",
            lambda: self._capture_coordinates(vars["x"], vars["y"], label="Spostamento"),
            "Ghost.TButton",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        ttk.Label(frame, text="Durata (s)", style="Body.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=vars["duration"], style="Modern.TEntry").grid(row=3, column=1, sticky="ew", pady=(12, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_drag_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {
            "start_x": tk.StringVar(),
            "start_y": tk.StringVar(),
            "end_x": tk.StringVar(),
            "end_y": tk.StringVar(),
            "duration": tk.StringVar(value="0.30"),
            "button": tk.StringVar(value="left"),
        }
        self._form_frames["Trascina"] = frame
        self._form_vars["Trascina"] = vars

        ttk.Label(frame, text="Partenza X", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["start_x"], style="Modern.TEntry").grid(row=0, column=1, sticky="ew")
        ttk.Label(frame, text="Partenza Y", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=vars["start_y"], style="Modern.TEntry").grid(row=1, column=1, sticky="ew", pady=(8, 0))
        self._button(
            frame,
            "Cattura partenza",
            lambda: self._capture_coordinates(vars["start_x"], vars["start_y"], label="Trascinamento (start)"),
            "Ghost.TButton",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        ttk.Label(frame, text="Arrivo X", style="Body.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=vars["end_x"], style="Modern.TEntry").grid(row=3, column=1, sticky="ew", pady=(12, 0))
        ttk.Label(frame, text="Arrivo Y", style="Body.TLabel").grid(row=4, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=vars["end_y"], style="Modern.TEntry").grid(row=4, column=1, sticky="ew", pady=(12, 0))
        self._button(
            frame,
            "Cattura arrivo",
            lambda: self._capture_coordinates(vars["end_x"], vars["end_y"], label="Trascinamento (arrivo)"),
            "Ghost.TButton",
        ).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        ttk.Label(frame, text="Durata (s)", style="Body.TLabel").grid(row=6, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=vars["duration"], style="Modern.TEntry").grid(row=6, column=1, sticky="ew", pady=(12, 0))
        ttk.Label(frame, text="Pulsante", style="Body.TLabel").grid(row=7, column=0, sticky="w", pady=(12, 0))
        combo = ttk.Combobox(frame, textvariable=vars["button"], values=("left", "right", "middle"), state="readonly")
        combo.grid(row=7, column=1, sticky="ew", pady=(12, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_keys_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {"keys": tk.StringVar(), "hold": tk.StringVar(value="0.05")}
        self._form_frames["Tasti"] = frame
        self._form_vars["Tasti"] = vars

        ttk.Label(frame, text="Sequenza tasti (usa + o , come separatori)", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["keys"], style="Modern.TEntry").grid(row=0, column=1, sticky="ew")
        ttk.Label(frame, text="Pausa tra pressioni (s)", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(frame, textvariable=vars["hold"], style="Modern.TEntry").grid(row=1, column=1, sticky="ew", pady=(12, 0))

        helper = (
            "Esempi: ctrl+shift+s, win+d, alt+tab, oppure lettere e numeri (a, 1, space)."
        )
        ttk.Label(frame, text=helper, style="Muted.TLabel", wraplength=320, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_text_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {"interval": tk.StringVar(value="0.02")}
        self._form_frames["Testo"] = frame
        self._form_vars["Testo"] = vars

        ttk.Label(frame, text="Testo da digitare", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        text_widget = tk.Text(
            frame,
            height=4,
            wrap="word",
            bg="#111827",
            fg=self.TEXT_MAIN,
            insertbackground=self.TEXT_MAIN,
            relief="flat",
        )
        text_widget.configure(highlightthickness=1, highlightbackground="#334155", highlightcolor=self.ACCENT)
        text_widget.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(6, 12))
        self._text_widgets["Testo"] = text_widget

        ttk.Label(frame, text="Intervallo tra caratteri (s)", style="Body.TLabel").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["interval"], style="Modern.TEntry").grid(row=2, column=1, sticky="ew", pady=(6, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)

    def _build_wait_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {"seconds": tk.StringVar(value="1.0")}
        self._form_frames["Attesa"] = frame
        self._form_vars["Attesa"] = vars

        ttk.Label(frame, text="Durata attesa (s)", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["seconds"], style="Modern.TEntry").grid(row=0, column=1, sticky="ew", pady=(6, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _build_scroll_form(self) -> None:
        frame = ttk.Frame(self.form_container, style="CardInner.TFrame")
        vars = {"amount": tk.StringVar(value="120"), "horizontal": tk.BooleanVar(value=False)}
        self._form_frames["Scroll"] = frame
        self._form_vars["Scroll"] = vars

        ttk.Label(frame, text="Quantità di scroll", style="Body.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=vars["amount"], style="Modern.TEntry").grid(row=0, column=1, sticky="ew", pady=(6, 0))
        ttk.Checkbutton(
            frame,
            text="Scorri orizzontalmente",
            variable=vars["horizontal"],
            style="Toggle.TCheckbutton",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(12, 0))

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    def _show_form(self, action_type: str) -> None:
        for frame in self._form_frames.values():
            frame.grid_forget()
        frame = self._form_frames[action_type]
        frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    # ------------------------------------------------------------------
    # Gestione azioni

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
        self.status_var.set(f"Aggiunta azione {action.label}")

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
        except KeyError:  # pragma: no cover - salvaguardia
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
            raise ValueError("Inserisci almeno un tasto o combinazione")
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
        self.status_var.set("Azioni selezionate rimosse")

    def _duplicate_selected(self) -> None:
        indices = self._selected_indices()
        if not indices:
            return
        for index in indices:
            self.actions.insert(index + 1, copy.deepcopy(self.actions[index]))
        self._refresh_tree()
        self._reselect([index + 1 for index in indices])
        self.status_var.set("Azioni duplicate accodate")

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

    def _export_sequence(self) -> None:
        if not self.actions:
            messagebox.showinfo(
                "Salvataggio sequenza",
                "Aggiungi almeno un'azione prima di salvare",
                parent=self.root,
            )
            return

        initial = self._last_sequence_path or "sequenza.json"
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Salva sequenza",
            initialfile=Path(initial).name,
            defaultextension=".json",
            filetypes=[
                ("Sequenze Eureka Autoclicker", "*.json"),
                ("Tutti i file", "*.*"),
            ],
        )
        if not path:
            return

        try:
            payload = serialize_actions(self.actions)
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(payload, fp, ensure_ascii=False, indent=2)
        except Exception as exc:  # pragma: no cover - dipende dal filesystem
            messagebox.showerror(
                "Salvataggio fallito",
                f"Impossibile salvare la sequenza:\n{exc}",
                parent=self.root,
            )
            return

        self._last_sequence_path = path
        self.status_var.set(f"Sequenza salvata in {Path(path).name}")

    def _import_sequence(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Carica sequenza",
            defaultextension=".json",
            filetypes=[
                ("Sequenze Eureka Autoclicker", "*.json"),
                ("Tutti i file", "*.*"),
            ],
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as fp:
                payload = json.load(fp)
            actions = deserialize_actions(payload)
        except ValueError as exc:
            messagebox.showerror(
                "Formato non valido",
                f"Il file selezionato non contiene una sequenza valida:\n{exc}",
                parent=self.root,
            )
            return
        except Exception as exc:  # pragma: no cover - dipende dal filesystem
            messagebox.showerror(
                "Caricamento fallito",
                f"Impossibile leggere il file:\n{exc}",
                parent=self.root,
            )
            return

        self.actions = actions
        self._last_sequence_path = path
        self._refresh_tree()
        if self.actions:
            self._select_index(0)
        self.status_var.set(f"Sequenza caricata da {Path(path).name}")

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

        try:
            countdown = self._parse_float(self.countdown_var.get(), "Countdown iniziale", minimum=0.0)
        except ValueError as exc:
            messagebox.showerror("Valore non valido", str(exc), parent=self.root)
            return

        loop = bool(self.loop_var.get())
        try:
            self.engine.start(self.actions, interval=interval, loop=loop, delay=countdown)
        except Exception as exc:  # pragma: no cover - dipende dall'ambiente grafico
            messagebox.showerror("Impossibile avviare", str(exc), parent=self.root)
            return

        if countdown > 0:
            self.status_var.set(f"Countdown iniziale di {countdown:.2f}s avviato")
            self._was_waiting = True
        else:
            self.status_var.set("Sequenza in esecuzione...")
            self._was_waiting = False
        self.start_btn.state(["disabled"])
        self.stop_btn.state(["!disabled"])

    def _stop_sequence(self) -> None:
        self.engine.stop()
        self.status_var.set("Sequenza arrestata")
        self.start_btn.state(["!disabled"])
        self.stop_btn.state(["disabled"])
        self._was_waiting = False

    def _poll_engine(self) -> None:
        running = self.engine.is_running()
        waiting = self.engine.is_waiting()

        if running:
            self.start_btn.state(["disabled"])
            self.stop_btn.state(["!disabled"])
            if waiting and not self._was_waiting:
                self.status_var.set("Countdown iniziale in corso...")
            if not waiting and (self._was_waiting or not self._was_running):
                self.status_var.set("Sequenza in esecuzione...")
        else:
            if self._was_running:
                self.status_var.set("Sequenza completata")
            self.start_btn.state(["!disabled"])
            self.stop_btn.state(["disabled"])

        self._was_running = running
        self._was_waiting = waiting
        self.root.after(200, self._poll_engine)

    def _on_close(self) -> None:
        if self.engine.is_running():
            self.engine.stop()
        self.root.destroy()

    # ------------------------------------------------------------------
    # Animazioni e utilità grafiche

    def _button(self, parent: tk.Misc, text: str, command, style: str) -> ttk.Button:
        btn = ttk.Button(parent, text=text, command=command, style=style)
        self._overlay.attach(btn, style)
        return btn

    def _animate_header_gradient(self) -> None:
        width = self.hero_canvas.winfo_width() or 600
        height = self.hero_canvas.winfo_height() or 180
        self.hero_canvas.delete("gradient")

        bands = 24
        for index in range(bands):
            phase = (self._hero_phase + index / bands) % 1.0
            color = self._gradient_color(phase)
            x0 = (width / bands) * index
            x1 = (width / bands) * (index + 1)
            self.hero_canvas.create_rectangle(x0, 0, x1, height, fill=color, outline="", tags="gradient")
        self.hero_canvas.lower()

        self._hero_phase = (self._hero_phase + 0.01) % 1.0
        self.root.after(60, self._animate_header_gradient)

    def _gradient_color(self, phase: float) -> str:
        palette = ["#312e81", "#4338ca", "#2563eb", "#38bdf8", "#6366f1"]
        index = int(phase * len(palette)) % len(palette)
        next_index = (index + 1) % len(palette)
        local_phase = phase * len(palette) - index
        return RippleOverlay._mix_color(palette[index], palette[next_index], local_phase)

    def _update_scroll_region(self, event: tk.Event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _stretch_content(self, event: tk.Event) -> None:
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.delta:
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_shift_mousewheel(self, event: tk.Event) -> None:
        if event.delta:
            self.canvas.xview_scroll(int(-event.delta / 120), "units")

    # ------------------------------------------------------------------
    # Utility di parsing e supporto

    def _capture_coordinates(self, x_var: tk.StringVar, y_var: tk.StringVar, *, label: str) -> None:
        if self._capture_toolkit is None:
            messagebox.showwarning(
                "Cattura non disponibile",
                "Installa pyautogui o pynput per usare la cattura della posizione",
                parent=self.root,
            )
            return

        position = self._capture_toolkit.get_position()
        if position is None:
            messagebox.showerror(
                "Cattura non riuscita",
                "Impossibile rilevare la posizione corrente del cursore",
                parent=self.root,
            )
            return

        x, y = position
        x_var.set(str(x))
        y_var.set(str(y))
        self.status_var.set(f"{label}: {x}, {y}")

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
