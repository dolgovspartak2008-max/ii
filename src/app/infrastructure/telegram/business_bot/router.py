"""Owner management panel handled by the main Telegram bot."""

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.application.tenants.use_cases import (
    GetOwnerDashboard,
    OnboardApprovedOwner,
    OwnerNotApproved,
    SetTenantAIEnabled,
    TenantNotFound,
    UpdateBusinessProfile,
)
from app.domain.tenants.entities import InvalidBusinessProfile
from app.infrastructure.telegram.business_bot.callbacks import OwnerPanelCallback

ACCESS_REQUIRED_TEXT = "Сначала подайте заявку через отдельный бот доступа."
BUSINESS_FORMAT_TEXT = "Формат: /business Название | Чем занимается бизнес"


class ProfileEdit(StatesGroup):
    name = State()
    description = State()
    confirmation = State()


def parse_business_profile(args: str | None) -> tuple[str, str] | None:
    """Parse the two owner-supplied business fields from a command argument."""
    name, separator, description = (args or "").partition("|")
    if not separator or not name.strip() or not description.strip():
        return None
    return name.strip(), description.strip()


def create_owner_panel_keyboard(ai_enabled: bool) -> InlineKeyboardMarkup:
    """Create the compact owner-only inline control panel."""
    ai_label = "🤖 ИИ: включён" if ai_enabled else "🤖 ИИ: выключен"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Мой бизнес",
                    callback_data=OwnerPanelCallback(action="show").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить описание",
                    callback_data=OwnerPanelCallback(action="edit").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=ai_label,
                    callback_data=OwnerPanelCallback(action="toggle_ai").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Как это работает",
                    callback_data=OwnerPanelCallback(action="help").pack(),
                )
            ],
        ]
    )


def create_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Сохранить",
                    callback_data=OwnerPanelCallback(action="confirm").pack(),
                ),
                InlineKeyboardButton(
                    text="✖️ Отмена",
                    callback_data=OwnerPanelCallback(action="cancel").pack(),
                ),
            ]
        ]
    )


async def render_panel(
    message: Message, dashboard: GetOwnerDashboard, owner_id: int
) -> None:
    data = await dashboard.execute(owner_id)
    await message.answer(
        "Панель управления", reply_markup=create_owner_panel_keyboard(data.ai_enabled)
    )


def create_business_router(
    onboarding: OnboardApprovedOwner,
    update_profile: UpdateBusinessProfile,
    set_ai_enabled: SetTenantAIEnabled,
    dashboard: GetOwnerDashboard,
) -> Router:
    """Create main-bot handlers that only operate on the sender's tenant."""
    router = Router(name="business-owner-settings")

    @router.message(CommandStart())
    @router.message(Command("admin"))
    async def start(message: Message) -> None:
        if message.from_user is None:
            return
        try:
            await onboarding.execute(message.from_user.id)
            await render_panel(message, dashboard, message.from_user.id)
        except OwnerNotApproved:
            await message.answer(ACCESS_REQUIRED_TEXT)

    @router.callback_query(OwnerPanelCallback.filter(F.action == "show"))
    async def show(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.message is None:
            return
        data = await dashboard.execute(callback.from_user.id)
        profile = data.profile
        text = (
            f"📋 Мой бизнес\nНазвание: {profile.name}\nОписание: {profile.description}"
            if profile is not None
            else "📋 Профиль бизнеса пока не заполнен."
        )
        await callback.message.answer(
            text, reply_markup=create_owner_panel_keyboard(data.ai_enabled)
        )
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "edit"))
    async def edit(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.from_user is None:
            return
        await state.set_state(ProfileEdit.name)
        await callback.message.answer("Введите название бизнеса.")
        await callback.answer()

    @router.message(ProfileEdit.name)
    async def receive_name(message: Message, state: FSMContext) -> None:
        if not message.text or not message.text.strip():
            await message.answer("Название не должно быть пустым. Введите его ещё раз.")
            return
        await state.update_data(name=message.text.strip())
        await state.set_state(ProfileEdit.description)
        await message.answer("Коротко опишите, чем занимается бизнес.")

    @router.message(ProfileEdit.description)
    async def receive_description(message: Message, state: FSMContext) -> None:
        if not message.text or not message.text.strip():
            await message.answer("Описание не должно быть пустым. Введите его ещё раз.")
            return
        await state.update_data(description=message.text.strip())
        data = await state.get_data()
        await state.set_state(ProfileEdit.confirmation)
        preview = (
            f"Проверьте профиль:\nНазвание: {data['name']}\n"
            f"Описание: {data['description']}"
        )
        await message.answer(
            preview,
            reply_markup=create_confirmation_keyboard(),
        )

    @router.callback_query(OwnerPanelCallback.filter(F.action == "confirm"))
    async def confirm(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.from_user is None:
            return
        data = await state.get_data()
        try:
            profile = await update_profile.execute(
                callback.from_user.id, data["name"], data["description"]
            )
        except (KeyError, InvalidBusinessProfile, TenantNotFound):
            await callback.message.answer(
                "Не удалось сохранить профиль. Начните заново."
            )
        else:
            await callback.message.answer(f"Бизнес сохранён: {profile.name}.")
        await state.clear()
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "cancel"))
    async def cancel(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.message.answer("Изменения отменены.")
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "toggle_ai"))
    async def toggle_ai(callback: CallbackQuery) -> None:
        if callback.from_user is None:
            return
        data = await dashboard.execute(callback.from_user.id)
        enabled = await set_ai_enabled.execute(
            callback.from_user.id, not data.ai_enabled
        )
        status = "включён" if enabled else "выключен"
        await callback.message.answer(
            f"ИИ {status}.", reply_markup=create_owner_panel_keyboard(enabled)
        )
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "help"))
    async def help_panel(callback: CallbackQuery) -> None:
        await callback.message.answer(
            "ИИ отвечает клиентам только когда включён. Если вы сами отвечаете "
            "в клиентском чате, ИИ передаёт этот диалог вам."
        )
        await callback.answer()

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
