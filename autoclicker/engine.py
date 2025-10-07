"""Motore centrale per la gestione delle azioni di automazione."""

from __future__ import annotations

import abc
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Optional, Sequence

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pyautogui as PyAutoGuiModule


# ---------------------------------------------------------------------------
# Backend di input


def _load_pyautogui() -> Optional["PyAutoGuiModule"]:
    try:  # pragma: no cover - dipende dall'ambiente dell'utente
        import pyautogui
    except Exception:  # pragma: no cover - modulo opzionale
        return None

    pyautogui.FAILSAFE = False
    return pyautogui


def _load_pynput():
    try:  # pragma: no cover - dipende dall'ambiente dell'utente
        from pynput import keyboard, mouse
    except Exception:  # pragma: no cover - modulo opzionale
        return None

    return keyboard, mouse


class InputToolkit:
    """Astrazione sulle operazioni di input per mouse e tastiera."""

    def __init__(self) -> None:
        self._pyautogui = _load_pyautogui()
        self._keyboard_controller = None
        self._mouse_controller = None

        if self._pyautogui is None:
            loaded = _load_pynput()
            if loaded is None:
                raise RuntimeError(
                    "Nessun backend disponibile: installa 'pyautogui' o 'pynput'"
                )

            keyboard_mod, mouse_mod = loaded
            self._keyboard_controller = keyboard_mod.Controller()
            self._mouse_controller = mouse_mod.Controller()
            self._keyboard_key_cls = keyboard_mod.Key
            self._mouse_button_cls = mouse_mod.Button
        else:
            self._keyboard_key_cls = None
            self._mouse_button_cls = None

    # ------------------------------------------------------------------
    # Utility di conversione

    _SPECIAL_KEYS = {
        "alt": "alt",
        "ctrl": "ctrl",
        "control": "ctrl",
        "shift": "shift",
        "win": "win",
        "command": "command",
        "cmd": "command",
        "option": "option",
        "enter": "enter",
        "return": "enter",
        "space": "space",
        "tab": "tab",
        "esc": "esc",
        "escape": "esc",
        "backspace": "backspace",
        "delete": "delete",
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right",
        "pageup": "pageup",
        "pagedown": "pagedown",
        "home": "home",
        "end": "end",
    }

    def _normalise_key(self, key: str) -> str:
        return key.strip().lower()

    # ------------------------------------------------------------------
    # Metodi pubblici

    def move_to(self, x: Optional[int], y: Optional[int], *, duration: float = 0.0) -> None:
        if x is None or y is None:
            return

        if self._pyautogui is not None:
            self._pyautogui.moveTo(x, y, duration=max(duration, 0.0))
        else:  # pragma: no cover - richiede interazione reale
            self._mouse_controller.position = (x, y)
            if duration > 0:
                time.sleep(duration)

    def click(
        self,
        *,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
    ) -> None:
        if self._pyautogui is not None:
            self._pyautogui.click(x=x, y=y, button=button)
            return

        button_obj = self._resolve_mouse_button(button)
        if x is not None and y is not None:
            self._mouse_controller.position = (x, y)
        self._mouse_controller.click(button_obj)

    def drag_to(
        self,
        x: int,
        y: int,
        *,
        duration: float = 0.3,
        button: str = "left",
    ) -> None:
        if self._pyautogui is not None:
            self._pyautogui.dragTo(x, y, duration=max(duration, 0.0), button=button)
            return

        button_obj = self._resolve_mouse_button(button)
        self._mouse_controller.press(button_obj)
        self._mouse_controller.position = (x, y)
        if duration > 0:
            time.sleep(duration)
        self._mouse_controller.release(button_obj)

    def scroll(self, amount: int, *, horizontal: bool = False) -> None:
        if self._pyautogui is not None:
            if horizontal:
                self._pyautogui.hscroll(amount)
            else:
                self._pyautogui.scroll(amount)
            return

        if horizontal:  # pragma: no cover - comportamento non facilmente testabile
            self._mouse_controller.scroll(amount, 0)
        else:
            self._mouse_controller.scroll(0, amount)

    def key_combo(self, keys: Sequence[str], *, hold: float = 0.05) -> None:
        if not keys:
            return

        if self._pyautogui is not None:
            normalised = [self._special_or_literal(k) for k in keys]
            if len(normalised) == 1:
                self._pyautogui.press(normalised[0])
            else:
                self._pyautogui.hotkey(*normalised, interval=max(hold, 0.0))
            return

        pressed = []
        for key in keys:  # pragma: no cover - dipende da interazione reale
            key_obj = self._resolve_key(key)
            self._keyboard_controller.press(key_obj)
            pressed.append(key_obj)
            if hold > 0:
                time.sleep(hold)
        for key_obj in reversed(pressed):
            self._keyboard_controller.release(key_obj)

    def type_text(self, text: str, *, interval: float = 0.0) -> None:
        if not text:
            return

        if self._pyautogui is not None:
            self._pyautogui.write(text, interval=max(interval, 0.0))
            return

        for char in text:  # pragma: no cover - richiede ambiente grafico
            self._keyboard_controller.press(char)
            self._keyboard_controller.release(char)
            if interval > 0:
                time.sleep(interval)

    # ------------------------------------------------------------------
    # Helper privati

    def _resolve_mouse_button(self, button: str):
        button = self._normalise_key(button)
        mapping = {
            "left": self._mouse_button_cls.left,
            "right": self._mouse_button_cls.right,
            "middle": self._mouse_button_cls.middle,
        }
        try:
            return mapping[button]
        except KeyError as exc:  # pragma: no cover - validazione run-time
            raise ValueError(f"Pulsante del mouse non supportato: {button}") from exc

    def _resolve_key(self, key: str):
        normalised = self._normalise_key(key)
        if normalised in self._SPECIAL_KEYS:
            mapped = self._SPECIAL_KEYS[normalised]
            if self._pyautogui is not None:
                return mapped
            return getattr(self._keyboard_key_cls, mapped)
        if self._pyautogui is not None:
            return normalised
        if len(normalised) == 1:
            return normalised
        try:
            return getattr(self._keyboard_key_cls, normalised)
        except AttributeError as exc:  # pragma: no cover - dipende dal layout
            raise ValueError(f"Tasto non supportato: {key}") from exc

    def _special_or_literal(self, key: str) -> str:
        normalised = self._normalise_key(key)
        return self._SPECIAL_KEYS.get(normalised, normalised)


class ExecutionContext:
    """Contesto passato alle azioni in esecuzione."""

    def __init__(self, toolkit: InputToolkit, stop_event: threading.Event) -> None:
        self.toolkit = toolkit
        self._stop_event = stop_event

    def wait(self, seconds: float) -> None:
        if seconds <= 0:
            return

        end_time = time.perf_counter() + seconds
        while not self._stop_event.is_set():
            remaining = end_time - time.perf_counter()
            if remaining <= 0:
                break
            self._stop_event.wait(min(0.1, remaining))

    @property
    def should_stop(self) -> bool:
        return self._stop_event.is_set()


# ---------------------------------------------------------------------------
# Azioni atomiche


class AutomationAction(abc.ABC):
    """Interfaccia base per le azioni dell'automazione."""

    @property
    def label(self) -> str:
        return self.__class__.__name__.replace("Action", "")

    @abc.abstractmethod
    def describe(self) -> str:
        """Restituisce una descrizione breve per l'interfaccia utente."""

    @abc.abstractmethod
    def execute(self, ctx: ExecutionContext) -> None:
        """Esegue l'azione utilizzando il contesto fornito."""


@dataclass(slots=True)
class ClickAction(AutomationAction):
    """Esegue uno o più click in una posizione opzionale."""

    x: Optional[int] = None
    y: Optional[int] = None
    button: str = "left"
    clicks: int = 1
    interval: float = 0.1

    def describe(self) -> str:
        parts = [self.button.capitalize()]
        if self.x is not None and self.y is not None:
            parts.append(f"@ ({self.x}, {self.y})")
        parts.append(f"x{self.clicks}")
        return " ".join(parts)

    def execute(self, ctx: ExecutionContext) -> None:
        for index in range(self.clicks):
            if ctx.should_stop:
                break
            ctx.toolkit.click(x=self.x, y=self.y, button=self.button)
            if index < self.clicks - 1 and self.interval > 0:
                ctx.wait(self.interval)


@dataclass(slots=True)
class MoveAction(AutomationAction):
    """Sposta il cursore in una posizione."""

    x: int
    y: int
    duration: float = 0.0

    def describe(self) -> str:
        return f"Verso ({self.x}, {self.y}) in {self.duration:.2f}s"

    def execute(self, ctx: ExecutionContext) -> None:
        ctx.toolkit.move_to(self.x, self.y, duration=self.duration)


@dataclass(slots=True)
class DragAction(AutomationAction):
    """Trascina il mouse verso una destinazione."""

    end_x: int
    end_y: int
    start_x: Optional[int] = None
    start_y: Optional[int] = None
    duration: float = 0.4
    button: str = "left"

    def describe(self) -> str:
        return f"{self.button.capitalize()} verso ({self.end_x}, {self.end_y})"

    def execute(self, ctx: ExecutionContext) -> None:
        if self.start_x is not None and self.start_y is not None:
            ctx.toolkit.move_to(self.start_x, self.start_y)
            ctx.wait(0.05)
        ctx.toolkit.drag_to(self.end_x, self.end_y, duration=self.duration, button=self.button)


@dataclass(slots=True)
class KeyPressAction(AutomationAction):
    """Premi una combinazione di tasti."""

    keys: Sequence[str]
    hold: float = 0.05

    def describe(self) -> str:
        combo = "+".join(self.keys)
        return f"Premi {combo}"

    def execute(self, ctx: ExecutionContext) -> None:
        ctx.toolkit.key_combo(self.keys, hold=self.hold)


@dataclass(slots=True)
class TypeTextAction(AutomationAction):
    """Digita un testo."""

    text: str
    interval: float = 0.0

    def describe(self) -> str:
        preview = self.text if len(self.text) <= 20 else self.text[:17] + "..."
        return f"Digita '{preview}'"

    def execute(self, ctx: ExecutionContext) -> None:
        ctx.toolkit.type_text(self.text, interval=self.interval)


@dataclass(slots=True)
class WaitAction(AutomationAction):
    """Attende un determinato intervallo di tempo."""

    seconds: float

    def describe(self) -> str:
        return f"Attendi {self.seconds:.2f}s"

    def execute(self, ctx: ExecutionContext) -> None:
        ctx.wait(self.seconds)


@dataclass(slots=True)
class ScrollAction(AutomationAction):
    """Esegue uno scroll verticale o orizzontale."""

    amount: int
    horizontal: bool = False

    def describe(self) -> str:
        axis = "orizz." if self.horizontal else "vert."
        return f"Scroll {axis} {self.amount}"

    def execute(self, ctx: ExecutionContext) -> None:
        ctx.toolkit.scroll(self.amount, horizontal=self.horizontal)


# ---------------------------------------------------------------------------
# Motore di esecuzione delle sequenze


@dataclass
class ActionEngine:
    """Esegue una sequenza di azioni di automazione."""

    interval: float = 0.0
    loop: bool = False
    _thread: Optional[threading.Thread] = field(init=False, default=None, repr=False)
    _stop_event: threading.Event = field(init=False, default_factory=threading.Event, repr=False)
    _toolkit: InputToolkit = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._toolkit = InputToolkit()

    def start(
        self,
        actions: Iterable[AutomationAction],
        *,
        interval: Optional[float] = None,
        loop: Optional[bool] = None,
    ) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Il motore è già in esecuzione")

        action_list = list(actions)
        if not action_list:
            raise ValueError("Nessuna azione da eseguire")

        if interval is not None:
            if interval < 0:
                raise ValueError("L'intervallo deve essere maggiore o uguale a zero")
            self.interval = interval
        if loop is not None:
            self.loop = loop

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._runner,
            args=(action_list,),
            daemon=True,
        )
        self._thread.start()

    def _runner(self, actions: Sequence[AutomationAction]) -> None:
        ctx = ExecutionContext(self._toolkit, self._stop_event)
        try:
            while not self._stop_event.is_set():
                for action in actions:
                    if self._stop_event.is_set():
                        break
                    action.execute(ctx)
                    if self._stop_event.is_set():
                        break
                    if self.interval > 0:
                        ctx.wait(self.interval)
                else:
                    if self.loop:
                        continue
                break
        finally:
            self._stop_event.set()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())


# ---------------------------------------------------------------------------
# Compatibilità con la CLI classica


@dataclass
class ClickEngine:
    """Motore semplificato per la modalità CLI."""

    interval: float = 0.1
    button: str = "left"
    _thread: Optional[threading.Thread] = field(init=False, default=None, repr=False)
    _stop_event: threading.Event = field(init=False, default_factory=threading.Event, repr=False)
    _toolkit: InputToolkit = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.interval <= 0:
            raise ValueError("L'intervallo deve essere maggiore di zero")
        self.button = self.button.lower()
        self._toolkit = InputToolkit()

    def click_once(self) -> None:
        self._toolkit.click(button=self.button)

    def _runner(
        self,
        *,
        count: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        start_time = time.perf_counter()
        performed = 0
        ctx = ExecutionContext(self._toolkit, self._stop_event)
        while not self._stop_event.is_set():
            if count is not None and performed >= count:
                break
            if duration is not None and (time.perf_counter() - start_time) >= duration:
                break

            self.click_once()
            performed += 1

            if count is not None and performed >= count:
                break
            if duration is not None and (time.perf_counter() - start_time) >= duration:
                break

            ctx.wait(self.interval)

    def run_blocking(
        self,
        *,
        count: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        self._stop_event.clear()
        try:
            self._runner(count=count, duration=duration)
        finally:
            self._stop_event.set()

    def start(
        self,
        *,
        count: Optional[int] = None,
        duration: Optional[float] = None,
    ) -> None:
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Il motore è già in esecuzione")

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._runner,
            kwargs={"count": count, "duration": duration},
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
