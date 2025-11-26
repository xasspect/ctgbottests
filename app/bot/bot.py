import logging
from typing import Dict, List, Optional
# from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from app.config.config import Config
# from app.bot.handlers.base_handler import BaseMessageHandler
# from app.bot.handlers.start_handler import StartHandler
# from app.bot.handlers.category_handler import CategoryHandler
# from app.bot.handlers.generation_handler import GenerationHandler
# from app.bot.handlers.admin_handler import AdminHandler

# from app.services.mpstats_service import MPStatsService
# from app.services.openai_service import OpenAIService
# from app.services.content_service import ContentService
# from app.services.session_service import SessionService
# from app.services.validation_service import ValidationService

# from app.database.repositories.user_repository import UserRepository
# from app.database.repositories.category_repository import CategoryRepository
# from app.database.repositories.session_repository import SessionRepository

# from app.utils.logger import setup_loggingn

class ContentGeneratorBot:
    def __init__(self, config: Config):
        self.config = config
        self.database = None
        # ...

    async def initialize_database(self):
        """Инициализация базы данных"""
        from app.database import database

        try:
            database.connect()
            database.create_tables()
            self.database = database
            self.logger.info("✅ Database initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Database initialization failed: {e}")
            raise

    async def initialize(self):
        """Инициализация всех компонентов бота"""
        self.logger.info("Initializing Content Generator Bot...")

        # Инициализация БД первой
        await self.initialize_database()

        # Затем остальные компоненты
        await self._initialize_repositories()
        await self._initialize_services()
        await self._initialize_telegram_app()
        await self._initialize_handlers()

        self.logger.info("Bot initialization completed successfully")

    async def shutdown(self):
        """Корректное завершение работы"""
        if self.database:
            self.database.close()
        self.logger.info("✅ Database connection closed")