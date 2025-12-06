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
        self.config = config  # Сохраняем конфигурацию
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

        # Инициализация сервисов (теперь передаем config)
        await self._initialize_services()

        # Инициализация aiogram
        await self._initialize_aiogram()

        # Инициализация обработчиков (теперь передаем config)
        await self._initialize_handlers()

        self.logger.info("✅ Bot initialization completed")

    async def _initialize_repositories(self):
        """Инициализация репозиториев"""
        try:
            from app.database.repositories.user_repo import UserRepository
            from app.database.repositories.category_repo import CategoryRepository
            from app.database.repositories.session_repo import SessionRepository
            from app.database.repositories.content_repo import ContentRepository

            # Создаем экземпляры репозиториев
            user_repo = UserRepository()
            category_repo = CategoryRepository()
            session_repo = SessionRepository()
            content_repo = ContentRepository()

            self.repositories = {
                'user_repo': user_repo,
                'category_repo': category_repo,
                'session_repo': session_repo,
                'content_repo': content_repo,
            }

            self.logger.info(f"✅ Repositories initialized: {list(self.repositories.keys())}")

        except Exception as e:
            self.logger.error(f"❌ Error initializing repositories: {e}")
            # Создаем пустой словарь, чтобы избежать KeyError
            self.repositories = {}

    async def _initialize_services(self):
        """Инициализация сервисов"""
        from app.services.mpstats_service import MPStatsService
        from app.services.openai_service import OpenAIService
        from app.services.content_service import ContentService
        from app.services.mpstats_scraper_service import MPStatsScraperService

        try:
            # Инициализируем скрапер с конфигом
            scraper_service = MPStatsScraperService(self.config)
            await scraper_service.initialize_scraper()

            # Инициализируем другие сервисы
            mpstats_service = MPStatsService()
            openai_service = OpenAIService()

            # Инициализируем ContentService с зависимостями
            content_service = ContentService(mpstats_service, openai_service)

            self.services = {
                'mpstats': mpstats_service,
                'openai': openai_service,
                'content': content_service,
                'scraper': scraper_service
            }

            self.logger.info("✅ Services initialized")

        except Exception as e:
            self.logger.error(f"❌ Error initializing services: {e}")
            self.services = {}

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
        # Меняем порядок: GenerationHandler раньше CategoryHandler
        self.handlers = [
            StartHandler(self.config, self.services, self.repositories),
            GenerationHandler(self.config, self.services, self.repositories),  # Первый - команды
            CategoryHandler(self.config, self.services, self.repositories),  # Второй - общие обработчики
        ]

        for handler in self.handlers:
            if handler:
                await handler.register(self.dp)
                self.logger.info(f"✅ Registered handler: {handler.__class__.__name__}")
            else:
                self.logger.error(f"❌ Handler is None!")
    async def run(self):
        """Запуск бота"""
        self.logger.info("🤖 Starting bot polling...")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            self.logger.error(f"❌ Error in polling: {e}")
            raise

    async def shutdown(self):
        """Завершение работы"""
        self.logger.info("👋 Shutting down bot...")

        try:
            if self.bot:
                await self.bot.session.close()
                self.logger.info("✅ Bot session closed")

            # Очистка временных файлов скрапера
            if 'scraper' in self.services:
                self.services['scraper'].cleanup_downloads()
                self.logger.info("✅ Scraper downloads cleaned")

            from app.database.database import database
            if database:
                database.close()
                self.logger.info("✅ Database connection closed")

        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")

        self.logger.info("👋 Bot shutdown completed")