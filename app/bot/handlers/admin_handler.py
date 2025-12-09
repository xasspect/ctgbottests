# app/bot/handlers/admin_handler.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class AdminHandler(BaseMessageHandler):
    """Обработчик админ-меню"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()

    async def register(self, dp):
        """Регистрация обработчиков"""
        dp.include_router(self.router)
        self.router.message.register(self.admin_menu, Command(commands=["admin"]))
        self.router.callback_query.register(self.handle_admin_menu, F.data == "admin_menu")

    async def admin_menu(self, message: Message):
        """Меню администратора"""
        user_id = message.from_user.id

        # Проверяем, является ли пользователь администратором
        user_repo = self.repositories['user_repo']
        user = user_repo.get_by_telegram_id(user_id)

        if not user or (user.id != self.config.telegram.admin_id and user.role != 'admin'):
            await message.answer("❌ У вас нет доступа к админ-меню")
            return

        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Управление категориями", callback_data="admin_manage_categories")
        if user.id == self.config.telegram.admin_id:
            builder.button(text="👑 Назначить администратора", callback_data="admin_promote")
        builder.button(text="📊 Статистика", callback_data="admin_stats")
        builder.button(text="↩️ Назад", callback_data="back_to_main_menu")
        builder.adjust(1)

        await message.answer(
            "👑 <b>Админ-меню</b>\n\n"
            "Выберите действие:",
            reply_markup=builder.as_markup()
        )

    async def handle_admin_menu(self, callback: CallbackQuery):
        """Обработка нажатия кнопки 'Админ'"""
        await callback.answer()
        await self.admin_menu(callback.message)