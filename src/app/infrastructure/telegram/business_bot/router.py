"""Owner setup commands handled by the main Telegram bot."""

from aiogram import Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from app.application.tenants.use_cases import (
    OnboardApprovedOwner,
    OwnerNotApproved,
    TenantNotFound,
    UpdateBusinessProfile,
)
from app.domain.tenants.entities import InvalidBusinessProfile

ACCESS_REQUIRED_TEXT = "Сначала подайте заявку через отдельный бот доступа."
BUSINESS_FORMAT_TEXT = "Формат: /business Название | Чем занимается бизнес"


def parse_business_profile(args: str | None) -> tuple[str, str] | None:
    """Parse the two owner-supplied business fields from a command argument."""
    name, separator, description = (args or "").partition("|")
    if not separator or not name.strip() or not description.strip():
        return None
    return name.strip(), description.strip()


def create_business_router(
    onboarding: OnboardApprovedOwner,
    update_profile: UpdateBusinessProfile,
) -> Router:
    """Create main-bot handlers that only operate on the sender's tenant."""
    router = Router(name="business-owner-settings")

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        if message.from_user is None:
            return
        try:
            result = await onboarding.execute(message.from_user.id)
        except OwnerNotApproved:
            await message.answer(ACCESS_REQUIRED_TEXT)
            return

        if result.is_new:
            await message.answer(
                "Доступ подтверждён. Настройте бизнес командой:\n"
                "/business Название | Чем занимается бизнес"
            )
        else:
            await message.answer(
                "Ваш бизнес уже подключен. Чтобы обновить описание, используйте:\n"
                "/business Название | Чем занимается бизнес"
            )

    @router.message(Command("business"))
    async def save_business(message: Message, command: CommandObject) -> None:
        if message.from_user is None:
            return
        parsed = parse_business_profile(command.args)
        if parsed is None:
            await message.answer(BUSINESS_FORMAT_TEXT)
            return

        try:
            profile = await update_profile.execute(message.from_user.id, *parsed)
        except TenantNotFound:
            await message.answer("Сначала нажмите /start в этом боте.")
            return
        except InvalidBusinessProfile:
            await message.answer(BUSINESS_FORMAT_TEXT)
            return

        await message.answer(f"Бизнес сохранён: {profile.name}.")

    return router
