import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.bot.handlers.base_handler import BaseMessageHandler


class StartHandler(BaseMessageHandler):
    """Обработчик команды /start"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()

    async def register(self, dp):
        """Регистрация обработчиков"""
        dp.include_router(self.router)
        self.router.message.register(self.start_command, Command(commands=["start", "help"]))
        self.router.message.register(self.about_command, Command(commands=["about"]))

    async def start_command(self, message: Message):
        """Обработчик команды /start"""
        try:
            # Проверяем наличие репозиториев
            if not self.repositories:
                self.logger.error("❌ Repositories not initialized!")
                await message.answer(
                    "👋 <b>Добро пожаловать в Content Generator Bot!</b>\n\n"
                    "📊 Я помогу вам генерировать контент для ваших товаров.\n\n"
                    "Доступные команды:\n"
                    "/categories - Выбрать категорию и назначение\n"
                    "/generate - Сгенерировать контент\n"
                    "/reset - Сбросить текущую сессию\n"
                    "/about - О боте\n"
                    "/help - Помощь"
                )
                return

            # Получаем репозитории
            user_repo = self.repositories.get('user_repo')
            if not user_repo:
                self.logger.error("❌ user_repo not found in repositories!")
                await message.answer(
                    "👋 <b>Добро пожаловать в Content Generator Bot!</b>\n\n"
                    "📊 Я помогу вам генерировать контент для ваших товаров.\n\n"
                    "Доступные команды:\n"
                    "/categories - Выбрать категорию и назначение\n"
                    "/generate - Сгенерировать контент\n"
                    "/reset - Сбросить текущую сессию\n"
                    "/about - О боте\n"
                    "/help - Помощь"
                )
                return

            # Создаем/получаем пользователя
            user = user_repo.get_or_create(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

            await message.answer(
                f"👋 <b>Добро пожаловать, {message.from_user.first_name}!</b>\n\n"
                f"📊 <b>Content Generator Bot</b>\n\n"
                "Я помогу вам:\n"
                
                "✅ Генерировать SEO-оптимизированные заголовки и описания\n\n"
                "🛠 <b>Доступные команды:</b>\n"
                "/categories - Выбрать категорию и назначение\n"
                "/generate - Сгенерировать контент\n"
                "/reset - Сбросить текущую сессию\n"
                "/about - О боте\n"
                "/help - Помощь\n\n"
            )

        except Exception as e:
            self.logger.error(f"❌ Error in start_command: {e}", exc_info=True)
            await message.answer(
                "👋 <b>Добро пожаловать!</b>\n\n"
                "Произошла ошибка при инициализации. Попробуйте команду /categories"
            )

    async def about_command(self, message: Message):
        """Обработчик команды /about"""
        await message.answer(
            "🤖 <b>MPStats Content Generator Bot</b>\n\n"
            "📊 <b>Версия:</b> 1.0.0\n"
            "👨‍💻 <b>Разработчик:</b> oleja\n"
            "🔗 <b>Источник:</b> MPStats + OpenAI\n\n"
            "💡 <b>Возможности:</b>\n"
            "• Сбор данных с MPStats\n"
            "• Генерация SEO-контента\n"
            "• Автоматическая категоризация\n\n"
        )