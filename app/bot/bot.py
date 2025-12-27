# app/bot/bot.py - обновленная версия
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.bot.handlers.content_generation_handler import ContentGenerationHandler
from app.config.config import config
from app.bot.handlers.start_handler import StartHandler
from app.bot.handlers.category_handler import CategoryHandler
from app.bot.handlers.generation_handler import GenerationHandler
from app.bot.handlers.admin_handler import AdminHandler
from app.bot.handlers.session_handler import SessionHandler
from app.services import MPStatsService


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
        self.logger.info("Initializing Telegram Bot (aiogram)...")

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
        try:
            from app.database.repositories.user_repo import UserRepository
            from app.database.repositories.category_repo import CategoryRepository
            from app.database.repositories.session_repo import SessionRepository
            from app.database.repositories.content_repo import ContentRepository

            self.repositories = {
                'user_repo': UserRepository(),
                'category_repo': CategoryRepository(),
                'session_repo': SessionRepository(),
                'content_repo': ContentRepository(),
            }

            self.logger.info(f"✅ Repositories initialized: {list(self.repositories.keys())}")

        except Exception as e:
            self.logger.error(f"❌ Error initializing repositories: {e}")
            self.repositories = {}

    # app/bot/bot.py - в методе _initialize_services

    async def _initialize_services(self):
        """Инициализация сервисов"""
        from app.services.openai_service import OpenAIService
        from app.services.content_service import ContentService
        from app.services.prompt_service import PromptService
        from app.services.mpstats_scraper_service import MPStatsScraperService
        from app.services.data_collection_service import DataCollectionService

        try:
            openai_service = OpenAIService()
            mpstats_service = MPStatsService()
            content_service = ContentService(mpstats_service, openai_service)
            prompt_service = PromptService()
            scraper_service = MPStatsScraperService(self.config)

            # Создаем data_collection_service с services в kwargs
            data_collection_service = DataCollectionService(
                config=self.config,
                scraper_service=scraper_service,
                services={  # Передаем как именованный аргумент
                    'openai': openai_service,
                    'prompt': prompt_service,
                    'content': content_service
                }
            )

            self.services = {
                'openai': openai_service,
                'mpstats': mpstats_service,
                'content': content_service,
                'prompt': prompt_service,
                'scraper': scraper_service,
                'data_collection': data_collection_service,
            }

            self.logger.info("✅ Все сервисы инициализированы")
            self.logger.info(f"Available services: {list(self.services.keys())}")

        except Exception as e:
            self.logger.error(f"❌ Error initializing services: {e}")
            self.services = {
                'openai': OpenAIService(),
                'content': ContentService(None, OpenAIService())
            }

    async def _initialize_aiogram(self):
        """Инициализация aiogram"""
        try:
            self.bot = Bot(
                token=self.config.telegram.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            self.dp = Dispatcher()
            self.logger.info("✅ Aiogram initialized")
        except Exception as e:
            self.logger.error(f"❌ Error initializing aiogram: {e}")
            raise

    async def _initialize_handlers(self):
        """Инициализация обработчиков"""
        self.handlers = [
            StartHandler(self.config, self.services, self.repositories),
            CategoryHandler(self.config, self.services, self.repositories),
            GenerationHandler(self.config, self.services, self.repositories),
            SessionHandler(self.config, self.services, self.repositories),
            AdminHandler(self.config, self.services, self.repositories),
            ContentGenerationHandler(self.config, self.services, self.repositories),
        ]

        for handler in self.handlers:
            if handler:
                await handler.register(self.dp)
                self.logger.info(f"✅ Registered handler: {handler.__class__.__name__}")
            else:
                self.logger.error(f"❌ Handler is None!")

    async def run(self):
        """Запуск бота"""
        self.logger.info("✅ Starting bot polling...")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            self.logger.error(f"❌ Error in polling: {e}")
            raise

    async def shutdown(self):
        """Завершение работы"""
        self.logger.info("Shutting down bot...")

        try:
            if self.bot:
                await self.bot.session.close()
                self.logger.info("✅ Bot session closed")

            from app.database.database import database
            if database:
                database.close()
                self.logger.info("✅ Database connection closed")

        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")

        self.logger.info("Bot shutdown completed")