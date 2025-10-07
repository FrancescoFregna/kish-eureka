"""Package principale per il modulo autoclicker."""

from .engine import (
    ActionEngine,
    AutomationAction,
    ClickAction,
    ClickEngine,
    DragAction,
    KeyPressAction,
    MoveAction,
    ScrollAction,
    TypeTextAction,
    WaitAction,
)

__all__ = [
    "ActionEngine",
    "AutomationAction",
    "ClickAction",
    "ClickEngine",
    "DragAction",
    "KeyPressAction",
    "MoveAction",
    "ScrollAction",
    "TypeTextAction",
    "WaitAction",
]
