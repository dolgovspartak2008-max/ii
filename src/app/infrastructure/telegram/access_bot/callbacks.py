"""Typed callback payloads for access application review actions."""

from typing import Literal
from uuid import UUID

from aiogram.filters.callback_data import CallbackData


class AccessReviewCallback(CallbackData, prefix="access-review"):
    """An administrator's review action for a specific application."""

    action: Literal["approve", "reject"]
    application_id: UUID
