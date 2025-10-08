"""Package principale per il modulo autoclicker."""

from .engine import (
    ActionEngine,
    AutomationAction,
    ClickAction,
    ClickEngine,
    DragAction,
    KeyPressAction,
    MoveAction,
    deserialize_actions,
    serialize_actions,
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
    "deserialize_actions",
    "serialize_actions",
    "ScrollAction",
    "TypeTextAction",
    "WaitAction",
]
