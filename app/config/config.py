# app/config/config.py
import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv
# from app.utils.logger import log
# from app.utils.log_codes import LogCodes

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
    mpstats_key: str
    openai_key: str
    mpstats_email: str
    mpstats_pswd: str

    mpstats_base_url: str = "https://mpstats.io/api"
    mpstats_delay: float = 1.0
    mpstats_timeout: int = 30
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7
    openai_timeout: int = 30


@dataclass
class TelegramConfig:
    """Конфигурация Telegram бота"""
    bot_token: str
    admin_ids: List[int] = field(default_factory=list)
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
    base_dir: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    data_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "data"
    ))
    logs_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "logs"
    ))
    downloads_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "downloads"
    ))
    mpstats_downloads_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "downloads", "mpstats"
    ))
    keywords_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "keywords"
    ))

    def __post_init__(self):
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)
        os.makedirs(self.mpstats_downloads_dir, exist_ok=True)
        os.makedirs(self.keywords_dir, exist_ok=True)

    @property
    def log_file_path(self) -> str:
        return os.path.join(self.logs_dir, "bot.log")


@dataclass
class SeleniumConfig:
    """Конфигурация Selenium для MPStats"""
    chrome_driver_path: str = "/usr/local/bin/chromedriver"
    chrome_binary_path: str = "/usr/bin/google-chrome"
    headless: bool = True  # По умолчанию True
    stealth_mode: bool = True
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    window_size: str = "1920,1080"
    page_load_timeout: int = 30
    implicit_wait_timeout: int = 10
    use_docker_chrome: bool = True
    chrome_options: List[str] = field(default_factory=lambda: [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--disable-extensions",
        "--disable-notifications",
        "--start-maximized"
    ])


class Config:
    """Главный класс конфигурации приложения"""

    def __init__(self):
        self.is_docker = os.getenv('DOCKER_MODE', 'false').lower() == 'true'

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

        self.paths = PathsConfig()

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

        self.api = APIConfig(
            mpstats_key=self._get_required('MPSTATS_API_KEY'),
            openai_key=self._get_required('OPENAI_API_KEY'),
            mpstats_email=self._get_required('MPSTATS_EMAIL'),
            mpstats_pswd=self._get_required('MPSTATS_PSWD'),
            mpstats_base_url=os.getenv('MPSTATS_BASE_URL', 'https://mpstats.io/api'),
            mpstats_delay=float(os.getenv('MPSTATS_REQUEST_DELAY', '1.0')),
            mpstats_timeout=int(os.getenv('MPSTATS_TIMEOUT', '30')),
            openai_model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            openai_max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '4000')),
            openai_temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            openai_timeout=int(os.getenv('OPENAI_TIMEOUT', '30'))
        )

        self.telegram = TelegramConfig(
            bot_token=self._get_required('TELEGRAM_BOT_TOKEN'),
            parse_mode=os.getenv('TELEGRAM_PARSE_MODE', 'HTML'),
            disable_web_page_preview=self._get_bool('TELEGRAM_DISABLE_PREVIEW', True)
        )
        self.telegram.admin_ids = self._parse_admin_ids()

        # Получаем headless из .env
        headless_mode = self._get_bool('SELENIUM_HEADLESS', True)

        self.selenium = SeleniumConfig(
            chrome_driver_path=os.getenv('CHROME_DRIVER_PATH', '/usr/local/bin/chromedriver'),
            chrome_binary_path=os.getenv('CHROME_BINARY_PATH', '/usr/bin/google-chrome'),
            headless=headless_mode,  # <-- ЗДЕСЬ ПЕРЕДАЕМ ЗНАЧЕНИЕ ИЗ .ENV
            stealth_mode=self._get_bool('SELENIUM_STEALTH_MODE', True),
            user_agent=os.getenv('SELENIUM_USER_AGENT',
                                 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'),
            window_size=os.getenv('SELENIUM_WINDOW_SIZE', '1920,1080'),
            page_load_timeout=int(os.getenv('SELENIUM_PAGE_LOAD_TIMEOUT', '30')),
            implicit_wait_timeout=int(os.getenv('SELENIUM_IMPLICIT_WAIT', '10')),
            use_docker_chrome=self._get_bool('USE_DOCKER_CHROME', True),
            chrome_options=self._get_chrome_options(headless_mode)  # <-- ПЕРЕДАЕМ В ОПЦИИ
        )

        self.limits = LimitsConfig(
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '3600')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30')),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
        )

        self._print_config_info()

    def _parse_admin_ids(self) -> List[int]:
        admin_ids_str = os.getenv('TELEGRAM_ADMIN_ID', '').strip()
        if not admin_ids_str:
            return []
        admin_ids = []
        parts = [part.strip() for part in admin_ids_str.split(',') if part.strip()]
        for part in parts:
            try:
                admin_ids.append(int(part))
            except ValueError:
                pass
        return admin_ids

    def _get_database_url(self) -> str:
        db_url = self._get_required('DATABASE_URL')
        db_host = os.getenv('DB_HOST', 'localhost')
        if self.is_docker and 'localhost' in db_url and db_host != 'localhost':
            db_url = db_url.replace('localhost', db_host)
        if self.is_docker and '127.0.0.1' in db_url and db_host != '127.0.0.1':
            db_url = db_url.replace('127.0.0.1', db_host)
        return db_url

    def _get_chrome_options(self, headless: bool) -> List[str]:
        """Получить опции Chrome с учетом headless режима"""
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
        if headless:
            default_options.append("--headless=new")
            default_options.append("--disable-logging")
            default_options.append("--log-level=3")

        # Добавляем кастомные опции из окружения
        custom_options = os.getenv('CHROME_OPTIONS', '')
        if custom_options:
            default_options.extend([opt.strip() for opt in custom_options.split(',') if opt.strip()])

        return default_options

    def _get_required(self, key: str) -> str:
        value = os.getenv(key)
        if value is None:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    def _get_bool(self, key: str, default: bool = False) -> bool:
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ['true', '1', 'yes', 'on', 'y', 't']

    def _print_config_info(self):
        print("=" * 60)
        print(f"{self.app.name} v{self.app.version}")
        print(f"Environment: {self.app.env}")
        print(f"Docker mode: {self.app.docker_mode}")
        print(f"Debug mode: {self.app.debug}")
        print(f"Selenium headless: {self.selenium.headless}")  # <-- ДЛЯ ПРОВЕРКИ
        print("=" * 60)

    @property
    def is_development(self) -> bool:
        return self.app.env == 'development'


config = Config()