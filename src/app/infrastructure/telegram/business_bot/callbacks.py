"""Callback payloads for the owner management panel."""

from typing import Literal

from aiogram.filters.callback_data import CallbackData


class OwnerPanelCallback(CallbackData, prefix="owner-panel"):
    """A button action that is always scoped to the Telegram sender."""

    action: Literal["show", "edit", "toggle_ai", "help", "confirm", "cancel"]
