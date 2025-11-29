from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class CategoryHandler(BaseMessageHandler):
    """Обработчик выбора категории и назначения"""

    def __init__(self, services: dict, repositories: dict):
        super().__init__(services, repositories)
        self.router = Router()

    async def register(self, dp):
        dp.include_router(self.router)
        self.router.message.register(self.show_categories, Command(commands=["categories"]))
        self.router.message.register(self.reset_session, Command(commands=["reset"]))
        self.router.message.register(self.handle_purpose_input, F.text & ~F.command)
        self.router.callback_query.register(self.handle_category_select, F.data.startswith("category_"))

    async def show_categories(self, message: Message):
        """Показать список категорий"""
        user_id = message.from_user.id

        # Получаем категории из БД
        category_repo = self.repositories['category_repo']
        categories = category_repo.get_active_categories()

        if not categories:
            await message.answer("❌ <b>Категории временно недоступны</b>")
            return

        # Создаем клавиатуру с категориями
        builder = InlineKeyboardBuilder()
        for category in categories:
            builder.button(
                text=category.name,
                callback_data=f"category_{category.id}"
            )
        builder.adjust(1)  # По одной кнопке в строке

        await message.answer(
            "📁 <b>Выберите категорию товара:</b>",
            reply_markup=builder.as_markup()
        )

    async def handle_category_select(self, callback: CallbackQuery):
        """Обработка выбора категории"""
        user_id = callback.from_user.id
        category_id = callback.data.replace("category_", "")

        # Получаем категорию
        category_repo = self.repositories['category_repo']
        category = category_repo.get_by_id(category_id)

        if not category:
            await callback.answer("❌ Категория не найдена")
            return

        # Сохраняем в сессию
        session_repo = self.repositories['session_repo']
        try:
            session = session_repo.create_new_session(
                user_id=user_id,
                category_id=category_id,
                current_step="category_selected"
            )

            await callback.message.edit_text(
                f"✅ <b>Выбрана категория:</b> {category.name}\n\n"
                f"📝 {category.description}\n\n"
                "✏️ <b>Теперь укажите назначение товара текстовым сообщением</b>\n"
                "<i>Например: 'для игр', 'повседневная', 'спортивная', 'офисная'</i>"
            )
            await callback.answer()

        except Exception as e:
            self.logger.error(f"❌ Error creating session: {e}")
            await callback.message.edit_text(
                "❌ <b>Ошибка при создании сессии</b>\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
            await callback.answer()

    async def handle_purpose_input(self, message: Message):
        """Обработка ввода назначения товара"""
        user_id = message.from_user.id
        purpose_text = message.text.strip()

        # Проверяем активную сессию
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session or session.current_step != "category_selected":
            await message.answer(
                "⚠️ Сначала выберите категорию с помощью <code>/categories</code>"
            )
            return

        # Сохраняем назначение
        session.purpose = purpose_text
        session.current_step = "purpose_added"

        # Обновляем сессию в БД
        session_repo.update(session.id, purpose=purpose_text, current_step="purpose_added")

        await message.answer(
            f"✅ <b>Назначение сохранено:</b> {purpose_text}\n\n"
            "📋 <b>Хотите добавить дополнительные параметры?</b>\n"
            "<i>Напишите через запятую, например: 'высокая производительность, AMOLED дисплей, долгая батарея'</i>\n\n"
            "🔸 Или отправьте <code>нет</code> чтобы продолжить без доп. параметров"
        )

    async def reset_session(self, message: Message):
        """Сброс сессии"""
        user_id = message.from_user.id

        session_repo = self.repositories['session_repo']
        session_repo.deactivate_all_sessions(user_id)

        await message.answer(
            "🔄 <b>Сессия сброшена</b>\n"
            "Начните заново с <code>/categories</code>"
        )