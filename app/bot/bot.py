import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.config.config import config
from app.bot.handlers.start_handler import StartHandler
from app.bot.handlers.category_handler import CategoryHandler
from app.bot.handlers.generation_handler import GenerationHandler


class ContentGeneratorBot:
    """Главный класс Telegram бота на aiogram"""

    def __init__(self, config):
        self.config = config
        self.bot = None
        self.dp = None
        self.handlers = []
        self.services = {}
        self.repositories = {}
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Инициализация бота"""
        self.logger.info("🚀 Initializing Telegram Bot (aiogram)...")

        # Инициализация БД
        from app.database.database import database
        database.connect()
        database.create_tables()

        # Инициализация репозиториев
        await self._initialize_repositories()

        # Инициализация сервисов
        await self._initialize_services()

        # Инициализация aiogram
        await self._initialize_aiogram()

        # Инициализация обработчиков
        await self._initialize_handlers()

        self.logger.info("✅ Bot initialization completed")

    async def _initialize_repositories(self):
        """Инициализация репозиториев"""
        from app.database.repositories.user_repo import UserRepository
        from app.database.repositories.category_repo import CategoryRepository
        from app.database.repositories.session_repo import SessionRepository

        self.repositories = {
            'user_repo': UserRepository(),
            'category_repo': CategoryRepository(),
            'session_repo': SessionRepository(),
        }

    async def _initialize_services(self):
        """Инициализация сервисов"""
        # Пока используем заглушки, но структура для будущих сервисов
        # from app.services.mpstats_service import MPStatsService
        # from app.services.openai_service import OpenAIService
        # from app.services.content_service import ContentService
        #
        # self.services = {
        #     'mpstats': MPStatsService(),
        #     'openai': OpenAIService(),
        #     'content': ContentService(
        #         openai_service=OpenAIService(),
        #         mpstats_service=MPStatsService()
        #     )
        # }
        # self.logger.info("✅ Services initialized")

    async def _initialize_aiogram(self):
        """Инициализация aiogram"""
        self.bot = Bot(
            token=self.config.telegram.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.logger.info("✅ Aiogram initialized")

    async def _initialize_handlers(self):
        """Инициализация обработчиков"""
        self.handlers = [
            StartHandler(self.services, self.repositories),
            CategoryHandler(self.services, self.repositories),
            GenerationHandler(self.services, self.repositories),
        ]

        for handler in self.handlers:
            await handler.register(self.dp)
            self.logger.info(f"✅ Registered handler: {handler.__class__.__name__}")

    async def run(self):
        """Запуск бота"""
        self.logger.info("🤖 Starting bot polling...")
        await self.dp.start_polling(self.bot)

    async def shutdown(self):
        """Завершение работы"""
        if self.bot:
            await self.bot.session.close()
        from app.database.database import database
        database.close()
        self.logger.info("👋 Bot shutdown completed")