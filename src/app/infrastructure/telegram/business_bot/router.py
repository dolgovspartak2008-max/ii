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

from app.application.chats.use_cases import (
    ListOwnerHandoffChats,
    ResumeOwnerChatAI,
)
from app.application.tenants.use_cases import (
    GetOwnerDashboard,
    OnboardApprovedOwner,
    OwnerNotApproved,
    SetTenantAIEnabled,
    TenantNotFound,
    UpdateBusinessProfile,
)
from app.domain.chats.entities import CustomerChat
from app.domain.tenants.entities import InvalidBusinessProfile
from app.infrastructure.telegram.business_bot.callbacks import (
    OwnerChatCallback,
    OwnerPanelCallback,
)

ACCESS_REQUIRED_TEXT = "Сначала подайте заявку через отдельный бот доступа."
BUSINESS_FORMAT_TEXT = "Формат: /business Название | Чем занимается бизнес"
START_REQUIRED_TEXT = "Сначала откройте панель командой /start."


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
                    text="✏️ Изменить профиль",
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
                    text="💬 Диалоги у вас",
                    callback_data=OwnerPanelCallback(action="chats").pack(),
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


def create_handoff_chats_keyboard(chats: list[CustomerChat]) -> InlineKeyboardMarkup:
    """Create resume controls without exposing a tenant identifier."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"Передать ИИ: чат {chat.telegram_chat_id}",
                callback_data=OwnerChatCallback(
                    action="resume", telegram_chat_id=chat.telegram_chat_id
                ).pack(),
            )
        ]
        for chat in chats
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=OwnerPanelCallback(action="back").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def render_panel(
    message: Message, dashboard: GetOwnerDashboard, owner_id: int
) -> None:
    """Render the latest state instead of trusting stale callback data."""
    data = await dashboard.execute(owner_id)
    await message.answer(
        "Панель управления",
        reply_markup=create_owner_panel_keyboard(data.ai_enabled),
    )


async def open_owner_panel(
    message: Message,
    state: FSMContext,
    owner_id: int,
    onboarding: OnboardApprovedOwner,
    dashboard: GetOwnerDashboard,
) -> None:
    """Clear unfinished edits and open the panel for one approved owner."""
    await state.clear()
    try:
        await onboarding.execute(owner_id)
        await render_panel(message, dashboard, owner_id)
    except OwnerNotApproved:
        await message.answer(ACCESS_REQUIRED_TEXT)
    except TenantNotFound:
        await message.answer(START_REQUIRED_TEXT)


async def render_panel_or_request_start(
    message: Message, dashboard: GetOwnerDashboard, owner_id: int
) -> None:
    try:
        await render_panel(message, dashboard, owner_id)
    except TenantNotFound:
        await message.answer(START_REQUIRED_TEXT)


def create_business_router(
    onboarding: OnboardApprovedOwner,
    update_profile: UpdateBusinessProfile,
    set_ai_enabled: SetTenantAIEnabled,
    dashboard: GetOwnerDashboard,
    handoffs: ListOwnerHandoffChats,
    resume: ResumeOwnerChatAI,
) -> Router:
    """Create main-bot handlers that only operate on the sender's tenant."""
    router = Router(name="business-owner-settings")

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext) -> None:
        if message.from_user is None:
            return
        await open_owner_panel(
            message,
            state,
            message.from_user.id,
            onboarding,
            dashboard,
        )

    @router.message(Command("admin"))
    async def admin(message: Message, state: FSMContext) -> None:
        if message.from_user is None:
            return
        await open_owner_panel(
            message,
            state,
            message.from_user.id,
            onboarding,
            dashboard,
        )

    @router.callback_query(OwnerPanelCallback.filter(F.action == "show"))
    async def show(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        try:
            data = await dashboard.execute(callback.from_user.id)
            profile = data.profile
            text = (
                "📋 Мой бизнес\n"
                f"Название: {profile.name}\n"
                f"Описание: {profile.description}"
                if profile is not None
                else "📋 Профиль бизнеса пока не заполнен."
            )
            await callback.message.answer(
                text,
                reply_markup=create_owner_panel_keyboard(data.ai_enabled),
            )
        except TenantNotFound:
            await callback.message.answer(START_REQUIRED_TEXT)
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "edit"))
    async def edit(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
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
        await message.answer(preview, reply_markup=create_confirmation_keyboard())

    @router.callback_query(OwnerPanelCallback.filter(F.action == "confirm"))
    async def confirm(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
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
            await render_panel_or_request_start(
                callback.message,
                dashboard,
                callback.from_user.id,
            )
        await state.clear()
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "cancel"))
    async def cancel(callback: CallbackQuery, state: FSMContext) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        await state.clear()
        await callback.message.answer("Изменения отменены.")
        await render_panel_or_request_start(
            callback.message,
            dashboard,
            callback.from_user.id,
        )
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "toggle_ai"))
    async def toggle_ai(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        try:
            data = await dashboard.execute(callback.from_user.id)
            enabled = await set_ai_enabled.execute(
                callback.from_user.id,
                not data.ai_enabled,
            )
        except TenantNotFound:
            await callback.message.answer(START_REQUIRED_TEXT)
        else:
            status = "включён" if enabled else "выключен"
            await callback.message.answer(f"ИИ {status}.")
            await render_panel_or_request_start(
                callback.message,
                dashboard,
                callback.from_user.id,
            )
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "chats"))
    async def list_handoff_chats(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        try:
            chats = await handoffs.execute(callback.from_user.id)
        except TenantNotFound:
            await callback.message.answer(START_REQUIRED_TEXT)
        else:
            text = (
                "Диалоги у вас. Выберите, какой из них снова передать ИИ."
                if chats
                else "Нет диалогов, переданных вам."
            )
            await callback.message.answer(
                text,
                reply_markup=create_handoff_chats_keyboard(chats),
            )
        await callback.answer()

    @router.callback_query(OwnerChatCallback.filter(F.action == "resume"))
    async def resume_chat(
        callback: CallbackQuery,
        callback_data: OwnerChatCallback,
    ) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        try:
            resumed = await resume.execute(
                callback.from_user.id,
                callback_data.telegram_chat_id,
            )
        except TenantNotFound:
            await callback.message.answer(START_REQUIRED_TEXT)
        else:
            text = (
                "Диалог передан ИИ."
                if resumed
                else "Этот диалог уже передан ИИ или недоступен."
            )
            await callback.message.answer(text)
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "back"))
    async def back(callback: CallbackQuery) -> None:
        if callback.from_user is None or callback.message is None:
            await callback.answer()
            return
        await render_panel_or_request_start(
            callback.message,
            dashboard,
            callback.from_user.id,
        )
        await callback.answer()

    @router.callback_query(OwnerPanelCallback.filter(F.action == "help"))
    async def help_panel(callback: CallbackQuery) -> None:
        if callback.message is not None:
            await callback.message.answer(
                "ИИ отвечает только когда включён. Если вы отвечаете клиенту сами, "
                "диалог передаётся вам. В разделе «Диалоги у вас» его можно "
                "вернуть ИИ."
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
            await message.answer(START_REQUIRED_TEXT)
            return
        except InvalidBusinessProfile:
            await message.answer(BUSINESS_FORMAT_TEXT)
            return
        await message.answer(f"Бизнес сохранён: {profile.name}.")
        await render_panel_or_request_start(message, dashboard, message.from_user.id)

    return router
