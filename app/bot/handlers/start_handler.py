# app/bot/handlers/start_handler.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler
from app.bot.handlers.snapshot_handler import SnapshotHandler


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
        self.router.callback_query.register(self.handle_show_snapshots, F.data == "show_snapshots")

    async def start(self, message: Message):
        """Обработка команды /start с проверкой доступа"""
        user_id = message.from_user.id

        # Проверяем, есть ли пользователь в списке администраторов
        if user_id not in self.config.telegram.admin_ids:
            await message.answer("⛔ У вас нет доступа к этому боту.")
            return

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

    async def handle_show_snapshots(self, callback: CallbackQuery):
        """Обработка нажатия кнопки 'История генераций'"""
        await callback.answer()

        # Передаем управление в SnapshotHandler
        from app.bot.handlers.snapshot_handler import SnapshotHandler
        snapshot_handler = SnapshotHandler(self.config, self.services, self.repositories)
        await snapshot_handler.show_snapshots(callback.message)

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
        builder.button(text="📸 История генераций", callback_data="show_snapshots")
        builder.button(text="ℹ️ О боте", callback_data="about_button")

        builder.adjust(2, 1)

        welcome_text = """
🤖 <b>Добро пожаловать в генератор контента для маркетплейсов!</b>

Я помогу вам создать оптимизированные заголовки и описания для карточек товаров на маркетплейсах.

📖 <b>Помощь по использованию бота</b>\n
1. Выбираете категорию товара
2. Указываете назначение и доп параметры
3. Нажмите кнопку \"Собрать данные\" и дождитесь пока mpstats вернет ключевые слова.
4. Выберите \"Меню генерации контента\" и сгенерируйте контент

/about - О боте
/help - Помощь
Разработчик - @ineedmorecode

<b>Нажмите "Начать" чтобы приступить к работе!</b>
"""

        await message.answer(welcome_text, reply_markup=builder.as_markup())

    async def handle_start_button(self, callback: CallbackQuery):
        """Обработка нажатия кнопки 'Начать'"""
        await callback.answer()
        from app.bot.handlers.category_handler import CategoryHandler
        category_handler = CategoryHandler(self.config, self.services, self.repositories)
        await category_handler.show_categories_command(callback.message)

    async def handle_help_button(self, callback: CallbackQuery):
        """Обработка кнопки 'Помощь'"""
        await callback.answer()
        await callback.message.answer(
            "📖 <b>Помощь по использованию бота</b>\n\n"
            "<b>Процесс работы:</b>\n"
            "1. Выберите категорию товара\n"
            "2. Укажите назначение и доп параметры\n"
            "3. Нажмите кнопку \"Собрать данные\" и дождитесь пока mpstats вернет ключевые слова."
            "4. Выберите \"Меню генерации контента\" и сгенерируйте контент \n\n"
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
            "• Сохранение истории генераций\n\n"
            "Для связи с разработчиком: @ineedmorecode"
        )

    async def handle_back_to_menu(self, callback: CallbackQuery):
        """Возврат в главное меню"""
        await callback.answer()
        user_id = callback.from_user.id
        user_repo = self.repositories['user_repo']
        user = user_repo.get_by_telegram_id(user_id)
        await self.show_welcome_message(callback.message, user)