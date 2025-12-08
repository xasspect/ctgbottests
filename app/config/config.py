# app/config/config.py
import os
from dataclasses import dataclass, field
from typing import Optional, List
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
    mpstats_email: str
    mpstats_pswd: str

    # Поля со значениями по умолчанию идут ПОСЛЕ
    mpstats_base_url: str = "https://mpstats.io/api"
    mpstats_delay: float = 1.0
    mpstats_timeout: int = 30
    openai_model: str = "gpt-3.5-turbo"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7
    openai_timeout: int = 30  # Таймаут для OpenAI API


@dataclass
class TelegramConfig:
    """Конфигурация Telegram бота"""
    bot_token: str
    admin_id: int
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = True


@dataclass
class AppConfig:
    """Конфигурация приложения"""
    env: str
    secret_key: str
    name: str = "MPStats Content Generator"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"

    # Docker-specific настройки
    docker_mode: bool = False
    container_name: str = "ctgbot"


@dataclass
class GenerationConfig:
    """Конфигурация генерации контента"""
    max_keywords: int = 50
    max_title_length: int = 60
    max_short_desc_length: int = 200
    max_long_desc_length: int = 500
    title_generation_attempts: int = 3
    description_generation_attempts: int = 3

    # Настройки для разных режимов генерации
    simple_generation_enabled: bool = True
    advanced_generation_enabled: bool = True


@dataclass
class LimitsConfig:
    """Конфигурация лимитов"""
    user_daily_limit: int = 50
    session_timeout: int = 3600
    request_timeout: int = 30
    max_concurrent_requests: int = 5


@dataclass
class PathsConfig:
    """Конфигурация путей"""
    # Базовые пути
    base_dir: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data"
    ))
    logs_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "logs"
    ))

    # Пути для загрузок
    downloads_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "downloads"
    ))
    mpstats_downloads_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "downloads", "mpstats"
    ))

    # Пути для ключевых слов
    keywords_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "keywords"
    ))

    def __post_init__(self):
        """Создаем директории если их нет"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)
        os.makedirs(self.mpstats_downloads_dir, exist_ok=True)
        os.makedirs(self.keywords_dir, exist_ok=True)

    @property
    def log_file_path(self) -> str:
        """Путь к файлу логов"""
        return os.path.join(self.logs_dir, "bot.log")


@dataclass
class SeleniumConfig:
    """Конфигурация Selenium для MPStats"""
    chrome_driver_path: str = "/usr/local/bin/chromedriver"
    chrome_binary_path: str = "/usr/bin/google-chrome"
    headless: bool = True  # В Docker лучше использовать headless режим
    stealth_mode: bool = True
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    window_size: str = "1920,1080"
    page_load_timeout: int = 30
    implicit_wait_timeout: int = 10

    # Настройки для Docker
    use_docker_chrome: bool = True
    chrome_options: List[str] = field(default_factory=lambda: [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-extensions",
        "--disable-notifications",
        "--start-maximized",
        "--headless=new"  # Новая версия headless режима
    ])


class Config:
    """
    Главный класс конфигурации приложения (только PostgreSQL)
    """

    def __init__(self):
        # Определяем режим Docker
        self.is_docker = os.getenv('DOCKER_MODE', 'false').lower() == 'true'

        # Приложение
        self.app = AppConfig(
            env=os.getenv('APP_ENV', 'development'),
            secret_key=self._get_required('SECRET_KEY'),
            name=os.getenv('APP_NAME', 'MPStats Content Generator'),
            version=os.getenv('APP_VERSION', '1.0.0'),
            debug=self._get_bool('DEBUG', False),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            docker_mode=self.is_docker,
            container_name=os.getenv('CONTAINER_NAME', 'ctgbot')
        )

        # Пути
        self.paths = PathsConfig()

        # PostgreSQL База данных (с поддержкой Docker)
        self.database = DatabaseConfig(
            url=self._get_database_url(),
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
            mpstats_email=self._get_required('MPSTATS_EMAIL'),
            mpstats_pswd=self._get_required('MPSTATS_PSWD'),
            mpstats_base_url=os.getenv('MPSTATS_BASE_URL', 'https://mpstats.io/api'),
            mpstats_delay=float(os.getenv('MPSTATS_REQUEST_DELAY', '1.0')),
            mpstats_timeout=int(os.getenv('MPSTATS_TIMEOUT', '30')),
            openai_model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            openai_max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '2000')),
            openai_temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            openai_timeout=int(os.getenv('OPENAI_TIMEOUT', '30'))
        )

        # Telegram
        self.telegram = TelegramConfig(
            bot_token=self._get_required('TELEGRAM_BOT_TOKEN'),
            admin_id=int(self._get_required('TELEGRAM_ADMIN_ID')),
            parse_mode=os.getenv('TELEGRAM_PARSE_MODE', 'HTML'),
            disable_web_page_preview=self._get_bool('TELEGRAM_DISABLE_PREVIEW', True)
        )

        # Selenium (с поддержкой Docker)
        self.selenium = SeleniumConfig(
            chrome_driver_path=os.getenv('CHROME_DRIVER_PATH', '/usr/local/bin/chromedriver'),
            chrome_binary_path=os.getenv('CHROME_BINARY_PATH', '/usr/bin/google-chrome'),
            headless=self._get_bool('SELENIUM_HEADLESS', True),
            stealth_mode=self._get_bool('SELENIUM_STEALTH_MODE', True),
            user_agent=os.getenv('SELENIUM_USER_AGENT',
                                 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
            window_size=os.getenv('SELENIUM_WINDOW_SIZE', '1920,1080'),
            page_load_timeout=int(os.getenv('SELENIUM_PAGE_LOAD_TIMEOUT', '30')),
            implicit_wait_timeout=int(os.getenv('SELENIUM_IMPLICIT_WAIT', '10')),
            use_docker_chrome=self._get_bool('USE_DOCKER_CHROME', True),
            chrome_options=self._get_chrome_options()
        )

        # Генерация контента
        self.generation = GenerationConfig(
            max_keywords=int(os.getenv('MAX_KEYWORDS', '50')),
            max_title_length=int(os.getenv('MAX_TITLE_LENGTH', '60')),
            max_short_desc_length=int(os.getenv('MAX_SHORT_DESC_LENGTH', '200')),
            max_long_desc_length=int(os.getenv('MAX_LONG_DESC_LENGTH', '500')),
            title_generation_attempts=int(os.getenv('TITLE_GENERATION_ATTEMPTS', '3')),
            description_generation_attempts=int(os.getenv('DESCRIPTION_GENERATION_ATTEMPTS', '3')),
            simple_generation_enabled=self._get_bool('SIMPLE_GENERATION_ENABLED', True),
            advanced_generation_enabled=self._get_bool('ADVANCED_GENERATION_ENABLED', True)
        )

        # Лимиты
        self.limits = LimitsConfig(
            user_daily_limit=int(os.getenv('USER_DAILY_LIMIT', '50')),
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '3600')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30')),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
        )

        # Выводим информацию о конфигурации
        self._print_config_info()

    def _get_database_url(self) -> str:
        """Получить URL базы данных с учетом Docker"""
        db_url = self._get_required('DATABASE_URL')
        db_host = os.getenv('DB_HOST', 'localhost')

        # Если мы в Docker и в URL указан localhost, заменяем на правильный хост
        if self.is_docker and 'localhost' in db_url and db_host != 'localhost':
            db_url = db_url.replace('localhost', db_host)
            print(f"Docker mode: Updated DATABASE_URL host to {db_host}")

        # Также заменяем 127.0.0.1
        if self.is_docker and '127.0.0.1' in db_url and db_host != '127.0.0.1':
            db_url = db_url.replace('127.0.0.1', db_host)

        return db_url

    def _get_chrome_options(self) -> List[str]:
        """Получить опции Chrome с учетом Docker"""
        default_options = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-extensions",
            "--disable-notifications",
            "--start-maximized",
        ]

        # Добавляем headless режим если нужно
        if self._get_bool('SELENIUM_HEADLESS', True):
            default_options.append("--headless=new")

        # Добавляем кастомные опции из окружения
        custom_options = os.getenv('CHROME_OPTIONS', '')
        if custom_options:
            default_options.extend([opt.strip() for opt in custom_options.split(',') if opt.strip()])

        return default_options

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
        return value.lower() in ['true', '1', 'yes', 'on', 'y', 't']

    def _print_config_info(self):
        """Вывести информацию о конфигурации"""
        print("=" * 60)
        print(f"{self.app.name} v{self.app.version}")
        print(f"Environment: {self.app.env}")
        print(f"Docker mode: {self.app.docker_mode}")
        print(f"Debug mode: {self.app.debug}")
        print(f"Database: {self.database.host}:{self.database.port}/{self.database.name}")
        print(f"Bot: {self.telegram.admin_id}")
        print(f"OpenAI: {self.api.openai_model}")
        print(f"MPStats: {self.api.mpstats_base_url}")
        print(f"Selenium headless: {self.selenium.headless}")
        print(f"Data dir: {self.paths.data_dir}")
        print(f"Logs dir: {self.paths.logs_dir}")
        print("=" * 60)

    @property
    def is_development(self) -> bool:
        return self.app.env == 'development'

    @property
    def is_production(self) -> bool:
        return self.app.env == 'production'

    @property
    def is_staging(self) -> bool:
        return self.app.env == 'staging'

    @property
    def is_testing(self) -> bool:
        return self.app.env == 'testing'

    def validate(self) -> bool:
        """Валидация конфигурации"""
        try:
            print("Validating configuration...")

            # Проверяем обязательные поля
            required_vars = [
                'DATABASE_URL', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
                'TELEGRAM_BOT_TOKEN', 'TELEGRAM_ADMIN_ID',
                'MPSTATS_API_KEY', 'OPENAI_API_KEY', 'SECRET_KEY',
                'MPSTATS_EMAIL', 'MPSTATS_PSWD'
            ]

            for var in required_vars:
                try:
                    self._get_required(var)
                    print(f"  ✅ {var}: OK")
                except ValueError as e:
                    print(f"  ❌ {var}: {e}")
                    return False

            # Валидация числовых значений
            if self.database.port <= 0:
                print(f"  ❌ DB_PORT must be positive: {self.database.port}")
                return False

            if self.generation.max_keywords <= 0:
                print(f"  ❌ MAX_KEYWORDS must be positive: {self.generation.max_keywords}")
                return False

            # Проверяем доступность директорий
            required_dirs = [
                self.paths.data_dir,
                self.paths.logs_dir,
                self.paths.downloads_dir,
                self.paths.mpstats_downloads_dir,
                self.paths.keywords_dir
            ]

            for directory in required_dirs:
                if not os.path.exists(directory):
                    print(f"  ❌ Directory doesn't exist, creating: {directory}")
                    os.makedirs(directory, exist_ok=True)
                if not os.access(directory, os.W_OK):
                    print(f"  ❌ Directory not writable: {directory}")
                    return False

            print("✅ Configuration validation passed!")
            return True

        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False

    def get_database_config_for_sqlalchemy(self) -> dict:
        """Получить конфигурацию для SQLAlchemy"""
        return {
            'url': self.database.url,
            'pool_size': self.database.pool_size,
            'max_overflow': self.database.max_overflow,
            'pool_timeout': self.database.pool_timeout,
            'pool_recycle': self.database.pool_recycle,
            'echo': self.app.debug
        }

    def get_openai_config(self) -> dict:
        """Получить конфигурацию для OpenAI"""
        return {
            'api_key': self.api.openai_key,
            'model': self.api.openai_model,
            'max_tokens': self.api.openai_max_tokens,
            'temperature': self.api.openai_temperature,
            'timeout': self.api.openai_timeout
        }

    def get_mpstats_config(self) -> dict:
        """Получить конфигурацию для MPStats"""
        return {
            'api_key': self.api.mpstats_key,
            'base_url': self.api.mpstats_base_url,
            'email': self.api.mpstats_email,
            'password': self.api.mpstats_pswd,
            'delay': self.api.mpstats_delay,
            'timeout': self.api.mpstats_timeout
        }

    def get_selenium_config(self) -> dict:
        """Получить конфигурацию для Selenium"""
        return {
            'chrome_driver_path': self.selenium.chrome_driver_path,
            'chrome_binary_path': self.selenium.chrome_binary_path,
            'headless': self.selenium.headless,
            'stealth_mode': self.selenium.stealth_mode,
            'user_agent': self.selenium.user_agent,
            'window_size': self.selenium.window_size,
            'page_load_timeout': self.selenium.page_load_timeout,
            'implicit_wait_timeout': self.selenium.implicit_wait_timeout,
            'use_docker_chrome': self.selenium.use_docker_chrome,
            'chrome_options': self.selenium.chrome_options
        }

    def __str__(self) -> str:
        """Строковое представление конфигурации (без паролей)"""
        return (
            f"AppConfig(\n"
            f"  env={self.app.env},\n"
            f"  debug={self.app.debug},\n"
            f"  docker_mode={self.app.docker_mode},\n"
            f"  log_level={self.app.log_level}\n"
            f")\n"
            f"DatabaseConfig(\n"
            f"  host={self.database.host},\n"
            f"  port={self.database.port},\n"
            f"  name={self.database.name},\n"
            f"  user={self.database.user}\n"
            f")\n"
            f"TelegramConfig(\n"
            f"  admin_id={self.telegram.admin_id},\n"
            f"  parse_mode={self.telegram.parse_mode}\n"
            f")\n"
            f"APIConfig(\n"
            f"  mpstats_base_url={self.api.mpstats_base_url},\n"
            f"  openai_model={self.api.openai_model},\n"
            f"  openai_max_tokens={self.api.openai_max_tokens}\n"
            f")"
        )


# Глобальный экземпляр конфигурации
config = Config()

# Автоматическая валидация при импорте
if __name__ == "__main__":
    print("Running configuration self-test...")
    if config.validate():
        print("✅ Configuration is valid!")
    else:
        print("❌ Configuration validation failed!")
        exit(1)