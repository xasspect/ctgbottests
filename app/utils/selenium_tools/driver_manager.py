# app/utils/selenium_tools/driver_manager.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager as WebDriverManager
from selenium.common.exceptions import TimeoutException
import os
import logging
from typing import Optional
import json
from app.services.chrome_driver_updater import ChromeDriverUpdater

try:
    from selenium_stealth import stealth

    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    logging.warning("selenium-stealth not installed. Install with: pip install selenium-stealth")

logger = logging.getLogger(__name__)


class ChromeDriverManager:
    """Управление Chrome драйвером с настройками для скачивания файлов, блокировкой медиа и stealth режимом."""

    def __init__(self, headless: bool = True, use_stealth: bool = True):
        """
        Инициализация менеджера Chrome драйвера.

        Args:
            headless: Режим без графического интерфейса
            use_stealth: Использовать selenium-stealth для сокрытия автоматизации
        """
        self.headless = headless
        self.use_stealth = use_stealth and HAS_STEALTH
        self.driver = None
        logger.info(f"ChromeDriverManager initialized: headless={headless}, stealth={self.use_stealth}")
        self.use_remote = os.getenv('USE_REMOTE_DRIVER', 'false').lower() == 'true'
        self.remote_url = os.getenv('SELENIUM_REMOTE_URL', 'http://localhost:4444/wd/hub')

    def get_downloaded_files(self, download_dir: Optional[str] = None):
        """
        Получает список скачанных файлов.

        Args:
            download_dir: Директория для скачивания (если None, используется последняя указанная)

        Returns:
            Список путей к скачанным файлам
        """
        if not download_dir:
            if hasattr(self, 'last_download_dir'):
                download_dir = self.last_download_dir
            else:
                download_dir = os.path.join(os.getcwd(), 'downloads')

        if not os.path.exists(download_dir):
            return []

        # Получаем все файлы, сортируем по времени изменения (сначала самые новые)
        files = []
        for filename in os.listdir(download_dir):
            filepath = os.path.join(download_dir, filename)
            if os.path.isfile(filepath):
                files.append({
                    'path': filepath,
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'modified': os.path.getmtime(filepath)
                })

        # Сортируем по времени изменения (сначала самые новые)
        files.sort(key=lambda x: x['modified'], reverse=True)
        return files

    def create_driver(
            self,
            download_dir: Optional[str] = None,
            block_videos: bool = True,
            block_images: bool = False,
            block_sounds: bool = True,
            block_animations: bool = True,
            disable_javascript: bool = False,
            user_agent: Optional[str] = None,
            proxy: Optional[str] = None,
            stealth_options: Optional[dict] = None,
            profile_dir: Optional[str] = None,  # НОВЫЙ ПАРАМЕТР
            keep_profile: bool = True  # НОВЫЙ ПАРАМЕТР
    ) -> webdriver.Chrome:
        """
        Создает и настраивает Chrome драйвер с stealth режимом.

        Args:
            download_dir: Папка для скачивания файлов
            block_videos: Блокировать видео
            block_images: Блокировать изображения
            block_sounds: Блокировать звуки
            block_animations: Блокировать анимации
            disable_javascript: Отключить JavaScript
            user_agent: Кастомный User-Agent
            proxy: Прокси сервер
            stealth_options: Дополнительные настройки stealth
            profile_dir: Путь к директории профиля Chrome
            keep_profile: Сохранять профиль между запусками

        Returns:
            Настроенный Chrome WebDriver
        """
        import app
        app_dir = os.path.dirname(os.path.dirname(app.__file__))

        # Явно устанавливаем путь для скачивания
        if download_dir:
            download_dir = os.path.join(app_dir, download_dir)
        else:
            download_dir = os.path.join(app_dir, 'downloads/mpstats')

        # Гарантируем, что директория существует
        os.makedirs(download_dir, exist_ok=True)

        # СОХРАНЯЕМ путь в атрибуте класса
        self.download_dir = download_dir
        self.last_download_dir = download_dir

        # Путь для профиля Chrome
        if profile_dir:
            # Используем переданный путь
            user_data_dir = profile_dir
        else:
            # Стандартный путь
            user_data_dir = os.path.join(app_dir, 'chrome_profile')

        # ИСПРАВЛЕНО: Важно - директория профиля должна существовать
        os.makedirs(user_data_dir, exist_ok=True)

        # ДОБАВЛЕНО: Проверка на наличие существующего профиля
        if keep_profile:
            logger.info(f"📁 Использую профиль Chrome (будет сохранен): {user_data_dir}")
            # Проверяем, есть ли уже сохраненные данные
            if os.path.exists(os.path.join(user_data_dir, 'Default')):
                logger.info("✅ Найден существующий профиль с данными")
            else:
                logger.info("🆕 Создаю новый профиль Chrome")
        else:
            logger.info(f"📁 Использую временный профиль Chrome (будет удален): {user_data_dir}")

        chrome_options = self._configure_chrome_options(
            user_data_dir=user_data_dir,
            download_dir=download_dir,
            block_videos=block_videos,
            block_images=block_images,
            block_sounds=block_sounds,
            block_animations=block_animations,
            disable_javascript=disable_javascript,
            user_agent=user_agent,
            proxy=proxy,
            keep_profile=keep_profile  # НОВЫЙ ПАРАМЕТР
        )

        driver = self._create_driver_with_options(chrome_options)

        # Применяем stealth режим
        if self.use_stealth:
            driver = self._apply_stealth_mode(driver, stealth_options)

        return driver

    def _configure_chrome_options(
            self,
            download_dir: str,
            user_data_dir: str,
            block_videos: bool,
            block_images: bool,
            block_sounds: bool,
            block_animations: bool,
            disable_javascript: bool,
            user_agent: Optional[str],
            proxy: Optional[str],
            keep_profile: bool = True  # НОВЫЙ ПАРАМЕТР
    ) -> ChromeOptions:
        chrome_options = ChromeOptions()

        # Базовые флаги для работы в контейнере
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")

        # ИСПРАВЛЕНО: Добавляем путь к профилю
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

        # ДОБАВЛЕНО: Используем конкретный профиль
        chrome_options.add_argument("--profile-directory=Default")

        # ДОБАВЛЕНО: Флаги для сохранения профиля
        if keep_profile:
            # Эти флаги помогают сохранять куки и сессии
            chrome_options.add_argument("--disable-session-crashed-bubble")
            chrome_options.add_argument(
                "--disable-features=OptimizationGuideModelDownloading,OptimizationHintsFetching,OptimizationTargetPrediction,OptimizationHints")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-features=ChromeWhatsNewUI")

            # Сохраняем пароли и автозаполнение
            prefs = {
                "credentials_enable_service": True,
                "profile.password_manager_enabled": True,
                "profile.default_content_setting_values.notifications": 2,
            }
        else:
            prefs = {}

        # User-Agent (если не задан, ставим стандартный)
        if not user_agent:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")

        # Настройки загрузок
        download_prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }

        # Объединяем с существующими prefs
        prefs.update(download_prefs)
        chrome_options.add_experimental_option("prefs", prefs)

        # Минимальное скрытие автоматизации
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # ДОБАВЛЕНО: Дополнительные флаги для стабильности
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        return chrome_options

    def _create_driver_with_options(self, chrome_options: ChromeOptions) -> webdriver.Chrome:
        try:
            updater = ChromeDriverUpdater()
            driver_path = updater.get_driver_path()
            logger.info(f"🚀 Путь к ChromeDriver: {driver_path}")

            # Проверка существования файла
            if not os.path.exists(driver_path):
                logger.error(f"❌ Файл драйвера не существует: {driver_path}")
                raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")

            # Логируем все аргументы и опции
            logger.info(f"📋 Аргументы Chrome: {chrome_options.arguments}")
            logger.info(f"⚙️ Экспериментальные опции: {chrome_options.experimental_options}")

            service = ChromeService(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)

            self._configure_devtools(driver)
            self._remove_automation_flags(driver)

            self.driver = driver
            logger.info("✅ Chrome драйвер успешно создан")
            return driver

        except Exception as e:
            logger.error(f"❌ Ошибка при создании Chrome драйвера: {e}", exc_info=True)
            raise

    def _apply_stealth_mode(self, driver: webdriver.Chrome, stealth_options: Optional[dict] = None) -> webdriver.Chrome:
        """
        Применяет selenium-stealth для сокрытия автоматизации.

        Args:
            driver: Chrome WebDriver
            stealth_options: Дополнительные настройки stealth

        Returns:
            Модифицированный драйвер
        """
        if not HAS_STEALTH:
            logger.warning("selenium-stealth не установлен. Пропускаем stealth режим.")
            return driver

        try:
            # Стандартные настройки stealth
            default_options = {
                "languages": ["en-US", "en"],
                "vendor": "Google Inc.",
                "platform": "Win32",
                "webgl_vendor": "Intel Inc.",
                "renderer": "Intel Iris OpenGL Engine",
                "fix_hairline": True,
                "run_on_insecure_origins": True,
            }

            # Объединяем с пользовательскими настройками
            options = {**default_options, **(stealth_options or {})}

            # Применяем stealth
            stealth(
                driver,
                languages=options["languages"],
                vendor=options["vendor"],
                platform=options["platform"],
                webgl_vendor=options["webgl_vendor"],
                renderer=options["renderer"],
                fix_hairline=options["fix_hairline"],
                run_on_insecure_origins=options["run_on_insecure_origins"],
            )

            logger.info("✅ Stealth режим активирован")
            return driver

        except Exception as e:
            logger.error(f"Ошибка при применении stealth режима: {e}")
            return driver

    def _remove_automation_flags(self, driver: webdriver.Chrome):
        """
        Удаляет флаги автоматизации через выполнение JavaScript.
        """
        try:
            # Удаляем webdriver property
            driver.execute_script("""
                // Удаляем navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Модифицируем window.chrome
                window.chrome = {
                    runtime: {},
                };

                // Скрываем признаки автоматизации в permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Модифицируем plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Модифицируем languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });

                // Модифицируем connection
                Object.defineProperty(navigator, 'connection', {
                    get: () => ({
                        rtt: 100,
                        downlink: 10,
                        effectiveType: '4g',
                        saveData: false,
                        type: 'wifi'
                    })
                });

                // Модифицируем hardwareConcurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });

                // Модифицируем deviceMemory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
            """)

            # Скрываем CDP (Chrome DevTools Protocol) признаки
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false
                    });
                '''
            })

            logger.info("✅ Признаки автоматизации удалены")

        except Exception as e:
            logger.warning(f"Не удалось удалить признаки автоматизации: {e}")

    def _configure_devtools(self, driver: webdriver.Chrome):
        """
        Настраивает DevTools для блокировки медиа запросов.
        """
        try:
            # Используем Chrome DevTools Protocol для блокировки медиа
            driver.execute_cdp_cmd('Network.setBlockedURLs', {
                'urls': [
                    '*.mp4', '*.webm', '*.ogg', '*.avi', '*.mov', '*.wmv',
                    '*.flv', '*.mkv', '*.m4v', '*.mpg', '*.mpeg',
                    '*.3gp', '*.swf', '*.flac', '*.wav', '*.mp3',
                    '*.aac', '*.m4a', '*.gif', '*.webp', '*.apng',
                    '*.mng',
                    '*.woff2', '*.ttf', '*.otf',
                ]
            })

            # Отключаем кэширование медиа
            driver.execute_cdp_cmd('Network.setCacheDisabled', {
                'cacheDisabled': True
            })

            # Устанавливаем эмуляцию сети для ускорения загрузки
            driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                'offline': False,
                'downloadThroughput': 50 * 1024 * 1024,
                'uploadThroughput': 10 * 1024 * 1024,
                'latency': 5
            })

        except Exception as e:
            logger.warning(f"Не удалось настроить DevTools: {e}")

    def quit(self):
        """Закрывает драйвер."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome драйвер закрыт")
            except:
                logger.warning("Не удалось закрыть драйвер")
            finally:
                self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()