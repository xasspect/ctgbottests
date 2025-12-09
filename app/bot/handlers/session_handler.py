# app/bot/handlers/session_handler.py
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class SessionHandler(BaseMessageHandler):
    """Обработчик для работы с сессиями"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()

    async def register(self, dp):
        dp.include_router(self.router)
        self.router.message.register(self.show_user_sessions, Command(commands=["session"]))
        self.router.callback_query.register(self.handle_session_select, F.data.startswith("session_"))
        self.router.callback_query.register(self.handle_back_to_sessions, F.data == "back_to_sessions")
        self.router.callback_query.register(self.handle_back_to_menu_from_session, F.data == "back_to_main_menu")

    async def handle_back_to_menu_from_session(self, callback: CallbackQuery):
        """Возврат в главное меню из сессий"""
        await callback.answer()

        # Перенаправляем в StartHandler
        from app.bot.handlers.start_handler import StartHandler
        start_handler = StartHandler(self.config, self.services, self.repositories)
        user_id = callback.from_user.id
        user_repo = self.repositories['user_repo']
        user = user_repo.get_by_telegram_id(user_id)
        await start_handler.show_welcome_message(callback.message, user)

    async def show_user_sessions(self, message: Message):
        """Показать последние 5 сессий пользователя"""
        user_id = message.from_user.id

        if 'session_repo' not in self.repositories:
            await message.answer("❌ Репозиторий сессий не инициализирован")
            return

        session_repo = self.repositories['session_repo']

        # Получаем последние 5 сессий пользователя
        sessions = self._get_user_sessions(user_id, limit=5)

        if not sessions:
            await message.answer(
                "📭 <b>У вас еще нет сессий</b>\n\n"
                "Начните с команды /categories или нажмите кнопку 'Начать' в главном меню."
            )
            return

        builder = InlineKeyboardBuilder()
        for session in sessions:
            # Показываем только сессии с заголовком
            if session.generated_title:
                category_name = self._get_category_display_name(session.category_id)
                date_str = session.created_at.strftime("%d.%m %H:%M")
                # Обрезаем заголовок для кнопки
                title_preview = session.generated_title[:20] + "..." if len(
                    session.generated_title) > 20 else session.generated_title
                button_text = f"{category_name}: {title_preview}"
                builder.button(text=button_text, callback_data=f"session_{session.id}")

        # Проверяем, есть ли сессии с заголовком
        if not builder.buttons:  # Проверяем, есть ли кнопки
            await message.answer(
                "📭 <b>У вас еще нет завершенных сессий</b>\n\n"
                "Создайте и примите хотя бы один заголовок."
            )
            return

        builder.button(text="↩️ Назад", callback_data="back_to_main_menu")
        builder.adjust(1)

        await message.answer(
            "📚 <b>Ваши последние сессии:</b>\n\n"
            "Выберите сессию для просмотра:",
            reply_markup=builder.as_markup()
        )

    def _get_user_sessions(self, user_id: int, limit: int = 5):
        """Получить сессии пользователя с лимитом"""
        if 'session_repo' not in self.repositories:
            return []

        session_repo = self.repositories['session_repo']
        with session_repo.get_session() as session:
            from app.database.models.session import UserSession
            return (
                session.query(UserSession)
                .filter(UserSession.user_id == user_id)
                .filter(UserSession.generated_title.isnot(None))  # Только сессии с заголовком
                .order_by(UserSession.created_at.desc())
                .limit(limit)
                .all()
            )

    def _get_category_display_name(self, category_id: str) -> str:
        """Получить отображаемое название категории"""
        categories_data = {
            "electronics": "📱 Электроника",
            "clothing": "👕 Одежда и обувь",
            "home": "🏠 Дом и сад",
            "beauty": "💄 Красота и здоровье"
        }
        return categories_data.get(category_id, "Неизвестная категория")

    async def handle_session_select(self, callback: CallbackQuery):
        """Обработка выбора сессии"""
        session_id = callback.data.replace("session_", "")

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Получаем информацию о категории
        category_name = self._get_category_display_name(session.category_id)

        # Формируем текст с информацией о сессии
        text = f"📋 <b>Информация о сессии</b>\n\n"
        text += f"📅 <b>Дата:</b> {session.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        text += f"📁 <b>Категория:</b> {category_name}\n"
        text += f"🎯 <b>Назначение:</b> {session.purpose}\n"

        if session.additional_params:
            text += f"📝 <b>Доп. параметры:</b> {', '.join(session.additional_params)}\n"

        text += f"\n📝 <b>Заголовок:</b>\n<code>{session.generated_title}</code>\n"

        if session.keywords:
            text += f"\n🔑 <b>Ключевые слова:</b>\n{', '.join(session.keywords[:10])}\n"

        if session.short_description:
            text += f"\n📋 <b>Краткое описание:</b>\n{session.short_description}\n"

        if session.long_description:
            text += f"\n📖 <b>Подробное описание:</b>\n{session.long_description}\n"

        # Создаем кнопки для навигации
        builder = InlineKeyboardBuilder()
        builder.button(text="↩️ К списку сессий", callback_data="back_to_sessions")
        builder.button(text="🏠 В меню", callback_data="back_to_main_menu")
        builder.adjust(1)

        await callback.message.edit_text(
            text,
            reply_markup=builder.as_markup()
        )
        await callback.answer()

    async def handle_back_to_sessions(self, callback: CallbackQuery):
        """Возврат к списку сессий"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        sessions = self._get_user_sessions(user_id, limit=5)

        if not sessions:
            await callback.message.edit_text(
                "📭 <b>У вас еще нет сессий</b>\n\n"
                "Начните с команды /categories или нажмите кнопку 'Начать' в главном меню."
            )
            await callback.answer()
            return

        builder = InlineKeyboardBuilder()
        for session in sessions:
            category_name = self._get_category_display_name(session.category_id)
            date_str = session.created_at.strftime("%d.%m %H:%M")
            button_text = f"{category_name} ({date_str})"
            builder.button(text=button_text, callback_data=f"session_{session.id}")

        builder.button(text="↩️ Назад", callback_data="back_to_main_menu")
        builder.adjust(1)

        await callback.message.edit_text(
            "📚 <b>Ваши последние 5 сессий:</b>\n\n"
            "Выберите сессию для просмотра:",
            reply_markup=builder.as_markup()
        )
        await callback.answer()

