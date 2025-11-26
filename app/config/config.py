import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


@dataclass
class DatabaseConfig:
    """Конфигурация PostgreSQL базы данных"""
    url: str
    host: str
    port: int
    name: str
    user: str
    password: str
    pool_size: int = 20
    max_overflow: int = 30
    pool_timeout: int = 30
    pool_recycle: int = 3600

    @property
    def connection_string(self) -> str:
        """Возвращает полную строку подключения"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


@dataclass
class APIConfig:
    """Конфигурация внешних API"""
    # Обязательные поля без значений по умолчанию идут ПЕРВЫМИ
    mpstats_key: str
    openai_key: str

    # Поля со значениями по умолчанию идут ПОСЛЕ
    mpstats_base_url: str = "https://mpstats.io/api"
    mpstats_delay: float = 1.0
    mpstats_timeout: int = 30
    # openai_model: str = "gpt-4"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7


@dataclass
class TelegramConfig:
    """Конфигурация Telegram бота"""
    bot_token: str
    admin_id: int


@dataclass
class AppConfig:
    """Конфигурация приложения"""
    env: str
    secret_key: str
    name: str = "MPStats Content Generator"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"


@dataclass
class GenerationConfig:
    """Конфигурация генерации контента"""
    max_keywords: int = 50
    max_title_length: int = 60
    max_short_desc_length: int = 200
    max_long_desc_length: int = 500
    title_generation_attempts: int = 3
    description_generation_attempts: int = 3


@dataclass
class LimitsConfig:
    """Конфигурация лимитов"""
    user_daily_limit: int = 50
    session_timeout: int = 3600
    request_timeout: int = 30


class Config:
    """
    Главный класс конфигурации приложения (только PostgreSQL)
    """

    def __init__(self):
        # Приложение
        self.app = AppConfig(
            env=os.getenv('APP_ENV', 'development'),
            secret_key=self._get_required('SECRET_KEY'),
            name=os.getenv('APP_NAME', 'MPStats Content Generator'),
            version=os.getenv('APP_VERSION', '1.0.0'),
            debug=self._get_bool('DEBUG', False),
            log_level=os.getenv('LOG_LEVEL', 'INFO')
        )

        # PostgreSQL База данных
        self.database = DatabaseConfig(
            url=self._get_required('DATABASE_URL'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            name=self._get_required('DB_NAME'),
            user=self._get_required('DB_USER'),
            password=self._get_required('DB_PASSWORD'),
            pool_size=int(os.getenv('DB_POOL_SIZE', '20')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '30')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
            pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '3600'))
        )

        # API
        self.api = APIConfig(
            mpstats_key=self._get_required('MPSTATS_API_KEY'),
            openai_key=self._get_required('OPENAI_API_KEY'),
            mpstats_base_url=os.getenv('MPSTATS_BASE_URL', 'https://mpstats.io/api'),
            mpstats_delay=float(os.getenv('MPSTATS_REQUEST_DELAY', '1.0')),
            mpstats_timeout=int(os.getenv('MPSTATS_TIMEOUT', '30')),
            # openai_model=os.getenv('OPENAI_MODEL', 'gpt-4'),
            openai_max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '2000')),
            openai_temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
        )

        # Telegram
        self.telegram = TelegramConfig(
            bot_token=self._get_required('TELEGRAM_BOT_TOKEN'),
            admin_id=int(self._get_required('TELEGRAM_ADMIN_ID'))
        )

        # Генерация контента
        self.generation = GenerationConfig(
            max_keywords=int(os.getenv('MAX_KEYWORDS', '50')),
            max_title_length=int(os.getenv('MAX_TITLE_LENGTH', '60')),
            max_short_desc_length=int(os.getenv('MAX_SHORT_DESC_LENGTH', '200')),
            max_long_desc_length=int(os.getenv('MAX_LONG_DESC_LENGTH', '500')),
            title_generation_attempts=int(os.getenv('TITLE_GENERATION_ATTEMPTS', '3')),
            description_generation_attempts=int(os.getenv('DESCRIPTION_GENERATION_ATTEMPTS', '3'))
        )

        # Лимиты
        self.limits = LimitsConfig(
            user_daily_limit=int(os.getenv('USER_DAILY_LIMIT', '50')),
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '3600')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30'))
        )

    def _get_required(self, key: str) -> str:
        """Получить обязательную переменную окружения"""
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"❌ Required environment variable {key} is not set")
        return value

    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Получить переменную как boolean"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ['true', '1', 'yes', 'on', 'y']

    @property
    def is_development(self) -> bool:
        return self.app.env == 'development'

    @property
    def is_production(self) -> bool:
        return self.app.env == 'production'

    def validate(self) -> bool:
        """Валидация конфигурации"""
        try:
            # Проверяем обязательные поля
            required_vars = [
                'DATABASE_URL', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
                'TELEGRAM_BOT_TOKEN', 'TELEGRAM_ADMIN_ID',
                'MPSTATS_API_KEY', 'OPENAI_API_KEY', 'SECRET_KEY'
            ]

            for var in required_vars:
                self._get_required(var)

            # Валидация числовых значений
            if self.database.port <= 0:
                raise ValueError("DB_PORT must be positive")

            if self.generation.max_keywords <= 0:
                raise ValueError("MAX_KEYWORDS must be positive")

            return True

        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False

    def __str__(self) -> str:
        """Строковое представление конфигурации (без паролей)"""
        return (
            f"AppConfig(env={self.app.env}, debug={self.app.debug})\n"
            f"DatabaseConfig(host={self.database.host}, port={self.database.port}, "
            f"name={self.database.name}, user={self.database.user})\n"
            f"APIConfig(mpstats_base_url={self.api.mpstats_base_url})\n"
            f"TelegramConfig(admin_id={self.telegram.admin_id})"
        )


# Глобальный экземпляр конфигурации
config = Config()