import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.config.config import config

logger = logging.getLogger(__name__)


class Database:
    """Класс для управления подключением к PostgreSQL"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.Base = declarative_base()

    def connect(self):
        """Подключение к PostgreSQL"""
        try:
            # Используем настройки пула из конфигурации
            self.engine = create_engine(
                config.database.url,
                pool_size=config.database.pool_size,
                max_overflow=config.database.max_overflow,
                pool_timeout=config.database.pool_timeout,
                pool_recycle=config.database.pool_recycle,
                pool_pre_ping=True,
                echo=config.app.debug
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Тестируем подключение
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()

            logger.info("✅ PostgreSQL connection established")
            logger.info(f"📊 Database: {config.database.name} on {config.database.host}:{config.database.port}")

        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise

    def create_tables(self):
        """Создание всех таблиц в PostgreSQL"""
        try:
            from app.database.models.user import User
            from app.database.models.category import Category
            from app.database.models.session import UserSession
            from app.database.models.content import GeneratedContent

            self.Base.metadata.create_all(bind=self.engine)
            logger.info("✅ PostgreSQL tables created")

        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL tables: {e}")
            raise

    def get_session(self) -> Session:
        """Получение сессии БД"""
        if not self.SessionLocal:
            self.connect()

        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """Контекстный менеджер для сессий (для автоматического закрытия)"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Закрытие подключения к PostgreSQL"""
        if self.engine:
            self.engine.dispose()
            logger.info("✅ PostgreSQL connection closed")


# Глобальный экземпляр БД
database = Database()