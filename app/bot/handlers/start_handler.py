# app/bot/handlers/start_handler.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class StartHandler(BaseMessageHandler):
    """Обработчик старта и главного меню"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()

    async def register(self, dp):
        """Регистрация обработчиков"""
        dp.include_router(self.router)
        self.router.message.register(self.start, Command(commands=["start", "help", "about"]))
        self.router.message.register(self.handle_categories, Command(commands=["categories"]))
        self.router.message.register(self.handle_session, Command(commands=["session"]))
        self.router.callback_query.register(self.handle_start_button, F.data == "start_button")
        self.router.callback_query.register(self.handle_help_button, F.data == "help_button")
        self.router.callback_query.register(self.handle_about_button, F.data == "about_button")
        self.router.callback_query.register(self.handle_back_to_menu, F.data == "back_to_main_menu")

    async def start(self, message: Message):
        """Обработка команды /start и показ главного меню"""
        user_id = message.from_user.id

        # Создаем пользователя, если его нет
        user_repo = self.repositories['user_repo']
        user = user_repo.get_or_create(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        # Показываем приветственное сообщение с кнопками
        await self.show_welcome_message(message, user)

    async def handle_categories(self, message: Message):
        """Обработка команды /categories"""
        # Перенаправляем в CategoryHandler
        from app.bot.handlers.category_handler import CategoryHandler
        category_handler = CategoryHandler(self.config, self.services, self.repositories)
        await category_handler.show_categories_command(message)

    async def handle_session(self, message: Message):
        """Обработка команды /session"""
        # Перенаправляем в SessionHandler
        from app.bot.handlers.session_handler import SessionHandler
        session_handler = SessionHandler(self.config, self.services, self.repositories)
        await session_handler.show_user_sessions(message)

    async def show_welcome_message(self, message: Message, user=None):
        """Показать приветственное сообщение с кнопками"""
        if not user:
            user_repo = self.repositories['user_repo']
            user = user_repo.get_by_telegram_id(message.from_user.id)

        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Начать", callback_data="start_button")
        builder.button(text="📖 Помощь", callback_data="help_button")
        builder.button(text="ℹ️ О боте", callback_data="about_button")

        # Добавляем кнопку админа, если пользователь админ
        if user and (user.id == self.config.telegram.admin_id or user.role == 'admin'):
            builder.button(text="👑 Админ", callback_data="admin_menu")

        builder.adjust(2, 1)  # Располагаем кнопки

        welcome_text = """
🤖 <b>Добро пожаловать в генератор контента для маркетплейсов!</b>

Я помогу вам создать оптимизированные заголовки и описания для карточек товаров на маркетплейсах.

<b>Как это работает:</b>
1. Выбираете категорию товара
2. Указываете назначение и параметры
3. Генерируете продающий заголовок
4. Создаете описания (краткое и подробное)

<b>Доступные команды:</b>
/categories - Выбрать категорию товара
/generate - Сгенерировать контент
/session - Посмотреть последние сессии
/reset - Сбросить текущую сессию
/about - О боте
/help - Помощь

<b>Нажмите "Начать" чтобы приступить к работе!</b>
"""

        await message.answer(welcome_text, reply_markup=builder.as_markup())

    async def handle_start_button(self, callback: CallbackQuery):
        """Обработка нажатия кнопки 'Начать'"""
        await callback.answer()

        # Перенаправляем в CategoryHandler для показа категорий
        from app.bot.handlers.category_handler import CategoryHandler
        category_handler = CategoryHandler(self.config, self.services, self.repositories)
        await category_handler.show_categories_command(callback.message)

    async def handle_help_button(self, callback: CallbackQuery):
        """Обработка кнопки 'Помощь'"""
        await callback.answer()
        await callback.message.answer(
            "📖 <b>Помощь по использованию бота</b>\n\n"
            "<b>Основные команды:</b>\n"
            "/start - Главное меню\n"
            "/categories - Выбрать категорию товара\n"
            "/generate - Сгенерировать контент\n"
            "/session - Посмотреть последние сессии\n"
            "/reset - Сбросить текущую сессию\n\n"
            "<b>Процесс работы:</b>\n"
            "1. Выберите категорию товара\n"
            "2. Укажите назначение и параметры\n"
            "3. Сгенерируйте заголовок\n"
            "4. Создайте описания\n\n"
            "Для начала работы нажмите 'Начать' в главном меню."
        )

    async def handle_about_button(self, callback: CallbackQuery):
        """Обработка кнопки 'О боте'"""
        await callback.answer()
        await callback.message.answer(
            "ℹ️ <b>О боте</b>\n\n"
            "🤖 <b>Content Generator Bot</b>\n"
            "Версия: 1.0.0\n\n"
            "Этот бот помогает создавать оптимизированный контент для карточек товаров на маркетплейсах.\n\n"
            "<b>Возможности:</b>\n"
            "• Генерация продающих заголовков\n"
            "• Создание кратких и подробных описаний\n"
            "• Оптимизация под поиск на маркетплейсах\n"
            "• Сохранение истории генераций\n\n"
            "Для связи с разработчиком: @your_contact"
        )

    async def handle_back_to_menu(self, callback: CallbackQuery):
        """Возврат в главное меню"""
        await callback.answer()

        user_id = callback.from_user.id
        user_repo = self.repositories['user_repo']
        user = user_repo.get_by_telegram_id(user_id)

        await self.show_welcome_message(callback.message, user)