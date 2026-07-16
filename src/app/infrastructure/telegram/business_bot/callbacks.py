"""Callback payloads for the owner management panel."""

from typing import Literal

from aiogram.filters.callback_data import CallbackData


class OwnerPanelCallback(CallbackData, prefix="owner-panel"):
    """A button action that is always scoped to the Telegram sender."""

    action: Literal[
        "show",
        "edit",
        "toggle_ai",
        "chats",
        "help",
        "confirm",
        "cancel",
        "back",
    ]


class OwnerChatCallback(CallbackData, prefix="owner-chat"):
    """A chat action that is authorized by the callback sender's tenant."""

    action: Literal["resume"]
    telegram_chat_id: int
