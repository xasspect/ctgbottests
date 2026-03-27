# app/bot/bot.py - обновленная версия
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.bot.handlers.content_generation_handler import ContentGenerationHandler
from app.bot.handlers.manual_filter_handler import ManualFilterHandler  # ДОБАВИТЬ ИМПОРТ
from app.bot.handlers.snapshot_handler import SnapshotHandler
from app.config.config import config
from app.bot.handlers.start_handler import StartHandler
from app.bot.handlers.category_handler import CategoryHandler
from app.bot.handlers.generation_handler import GenerationHandler
from app.bot.handlers.session_handler import SessionHandler

from app.utils.logger import log
from app.utils.log_codes import LogCodes

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

    async def initialize(self):
        """Инициализация бота"""
        log.info(LogCodes.SYS_INIT, module="Bot")

        from app.database.database import database
        database.connect()
        database.create_tables()

        await self._sync_admin_users()
        await self._initialize_repositories()
        await self._initialize_services()
        await self._initialize_aiogram()
        await self._initialize_handlers()

        log.info(LogCodes.SYS_START)

    async def _sync_admin_users(self):
        """Синхронизирует список администраторов из конфигурации с базой данных."""
        try:
            admin_ids = self.config.telegram.admin_ids
            if not admin_ids:
                return

            user_repo = self.repositories.get('user_repo')
            if not user_repo:
                log.error(LogCodes.ERR_DATABASE, error="User repo not found")
                return

            for admin_id in admin_ids:
                try:
                    user = user_repo.get_or_create(
                        telegram_id=admin_id,
                        username=f"admin_{admin_id}",
                        first_name="Admin"
                    )
                    if user.role != 'admin':
                        user_repo.update(user.id, role='admin')
                except Exception as e:
                    log.error(LogCodes.ERR_DATABASE, error=f"Admin sync: {e}")

            log.info(LogCodes.DB_RECORD_UPDATED, table="users", id=f"{len(admin_ids)} admins")

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=f"Admin sync: {e}")

    async def _initialize_repositories(self):
        """Инициализация репозиториев"""
        try:
            from app.database.repositories.user_repo import UserRepository
            from app.database.repositories.category_repo import CategoryRepository
            from app.database.repositories.session_repo import SessionRepository
            from app.database.repositories.content_repo import ContentRepository
            from app.database.repositories.snapshot_repo import SnapshotRepository

            self.repositories = {
                'user_repo': UserRepository(),
                'category_repo': CategoryRepository(),
                'session_repo': SessionRepository(),
                'content_repo': ContentRepository(),
                'snapshot_repo': SnapshotRepository(),
            }

            log.info(LogCodes.DB_RECORD_CREATED, table="repositories", id=f"{len(self.repositories)}")

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=f"Repositories init: {e}")
            self.repositories = {}

    async def _initialize_services(self):
        """Инициализация сервисов (один раз при старте)"""
        from app.services.openai_service import OpenAIService
        from app.services.prompt_service import PromptService
        from app.services.mpstats_scraper_service import MPStatsScraperService
        from app.services.data_collection_service import DataCollectionService

        try:
            # Создаем сервисы один раз
            openai_service = OpenAIService()
            prompt_service = PromptService()
            scraper_service = MPStatsScraperService(self.config)

            data_collection_service = DataCollectionService(
                config=self.config,
                scraper_service=scraper_service,
                services={
                    'openai': openai_service,
                    'prompt': prompt_service,
                }
            )

            self.services = {
                'openai': openai_service,
                'prompt': prompt_service,
                'scraper': scraper_service,
                'data_collection': data_collection_service,
            }

            log.info(LogCodes.SYS_INIT, module="Services (singleton)")

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Services init: {e}")
            self.services = {}

    async def _initialize_aiogram(self):
        """Инициализация aiogram"""
        try:
            self.bot = Bot(
                token=self.config.telegram.bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
            self.dp = Dispatcher()
            log.info(LogCodes.SYS_INIT, module="Aiogram")
        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Aiogram init: {e}")
            raise

    async def _initialize_handlers(self):
        """Инициализация обработчиков"""
        self.handlers = [
            StartHandler(self.config, self.services, self.repositories),
            ManualFilterHandler(self.config, self.services, self.repositories),
            CategoryHandler(self.config, self.services, self.repositories),
            GenerationHandler(self.config, self.services, self.repositories),
            SessionHandler(self.config, self.services, self.repositories),
            ContentGenerationHandler(self.config, self.services, self.repositories),
            SnapshotHandler(self.config, self.services, self.repositories)
        ]

        for handler in self.handlers:
            if handler:
                await handler.register(self.dp)
                log.info(LogCodes.SYS_INIT, module=handler.__class__.__name__)

    async def run(self):
        """Запуск бота"""
        log.info(LogCodes.SYS_INIT, module="Polling")
        try:
            await self.dp.start_polling(self.bot)
        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Polling: {e}")
            raise


    async def shutdown(self):
        """Завершение работы"""
        log.info(LogCodes.SYS_SHUTDOWN)

        try:
            if self.bot:
                await self.bot.session.close()

            from app.database.database import database
            if database:
                database.close()

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Shutdown: {e}")

        log.info(LogCodes.SYS_STOP)