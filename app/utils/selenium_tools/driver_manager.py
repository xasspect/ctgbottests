from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager as WebDriverManager
from selenium.common.exceptions import TimeoutException
import os
import logging
from typing import Optional

try:
    from selenium_stealth import stealth

    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False
    logging.warning("selenium-stealth not installed. Install with: pip install selenium-stealth")

logger = logging.getLogger(__name__)


class ChromeDriverManager:
    """Управление Chrome драйвером с настройками для скачивания файлов, блокировкой медиа и stealth режимом."""

    def __init__(self, headless: bool = False, use_stealth: bool = True):
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

    def get_downloaded_files(self, download_dir: Optional[str] = None):
        """
        Получает список скачанных файлов.

        Args:
            download_dir: Директория для скачивания (если None, используется последняя указанная)

        Returns:
            Список путей к скачанным файлам
        """
        if not download_dir:
            # Можно сохранить download_dir при создании драйвера
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
            stealth_options: Optional[dict] = None
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

        Returns:
            Настроенный Chrome WebDriver
        """
        # ИСПРАВЛЕНО: Используем абсолютный путь для скачивания
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
        self.last_download_dir = download_dir  # Для совместимости

        # Путь для профиля Chrome
        user_data_dir = os.path.join(app_dir, 'chrome_profile')
        os.makedirs(user_data_dir, exist_ok=True)

        logger.info(f"📁 Использую профиль Chrome: {user_data_dir}")
        logger.info(f"📂 Директория для скачивания: {download_dir} (абсолютный путь)")

        chrome_options = self._configure_chrome_options(
            user_data_dir=user_data_dir,
            download_dir=download_dir,  # Передаем абсолютный путь
            block_videos=block_videos,
            block_images=block_images,
            block_sounds=block_sounds,
            block_animations=block_animations,
            disable_javascript=disable_javascript,
            user_agent=user_agent,
            proxy=proxy
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
            proxy: Optional[str]
    ) -> ChromeOptions:
        """
        Настраивает опции Chrome для обхода детекции.

        Returns:
            Настроенные ChromeOptions
        """
        chrome_options = ChromeOptions()

        chrome_options.add_argument(f"user-data-dir={user_data_dir}")

        # Основные флаги для обхода детекции
        chrome_flags = [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",

            # Флаги для обхода детекции автоматизации
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            "--allow-running-insecure-content",

            # Отключаем ненужные функции
            "--disable-features=MediaRouter",
            "--disable-component-update",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--metrics-recording-only",
            "--disable-client-side-phishing-detection",
            "--disable-hang-monitor",
            "--disable-prompt-on-repost",
            "--disable-domain-reliability",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-ipc-flooding-protection",
            "--disable-notifications",
            "--disable-popup-blocking",
            "--disable-site-isolation-trials",
            "--disable-logging",
            "--disable-breakpad",
            "--disable-software-rasterizer",
            "--disable-features=VizDisplayCompositor",
        ]

        # Специальные флаги для обхода детекции
        chrome_flags.extend([
            "--disable-blink-features=AutomationControlled",
            "--use-fake-ui-for-media-stream",  # Обход запроса разрешений
            "--use-fake-device-for-media-stream",  # Использование фейковых устройств
            "--disable-features=UserAgentClientHint",  # Отключаем Client Hints
            "--disable-webrtc",  # Отключаем WebRTC для скрытия IP
            "--disable-webrtc-hw-encoding",
            "--disable-webrtc-hw-decoding",
            "--disable-databases",
            "--disable-local-storage",
            "--disable-appcache",
            "--disable-file-system",
            "--enable-features=NetworkService,NetworkServiceInProcess",
        ])

        # Флаги для блокировки медиа
        if block_videos:
            chrome_flags.extend([
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=PreloadMediaEngagementData,AutoplayIgnoreWebAudio,MediaSession",
                "--disable-background-video-track",
                "--disable-pepper-3d",
                "--disable-pepper-3d-image-chromium",
            ])

        if block_sounds:
            chrome_flags.extend([
                "--mute-audio",
                "--disable-audio-output",
            ])

        if block_animations:
            chrome_flags.extend([
                "--force-prefers-reduced-motion",
            ])

        # Добавляем флаги в опции
        for flag in chrome_flags:
            chrome_options.add_argument(flag)

        if self.headless:
            chrome_options.add_argument("--headless=new")
            # Дополнительные флаги для headless режима
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--remote-debugging-address=0.0.0.0")

        # Настраиваем User-Agent
        if not user_agent:
            # Современный Chrome User-Agent для Windows
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        chrome_options.add_argument(f"user-agent={user_agent}")

        if proxy:
            chrome_options.add_argument(f'--proxy-server={proxy}')

        # Настройки для скачивания файлов
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
            "safebrowsing.disable_download_protection": True,
            "profile.default_content_settings.popups": 0,
            "profile.default_content_setting_values.automatic_downloads": 1,
            "profile.default_content_setting_values.notifications": 2,

            # Важно: отключаем предложение "Сохранить как..."
            "profile.content_settings.pattern_pairs.*.multiple-automatic-downloads": 1,

            # Настройки для обхода детекции
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "webrtc.ip_handling_policy": "disable_non_proxied_udp",
            "webrtc.multiple_routes_enabled": False,
            "webrtc.nonproxied_udp_enabled": False,
        }

        # Блокировка медиа через настройки контента
        if block_videos:
            prefs.update({
                "profile.default_content_setting_values.plugins": 2,
                "profile.default_content_setting_values.media_stream": 2,
                "profile.default_content_setting_values.media_playback": 2,
                "profile.content_settings.exceptions.plugins.*.setting": 2,
            })

        if block_images:
            prefs["profile.default_content_setting_values.images"] = 2

        if disable_javascript:
            prefs["profile.default_content_setting_values.javascript"] = 2

        chrome_options.add_experimental_option("prefs", prefs)

        # Критически важные опции для обхода детекции
        chrome_options.add_experimental_option("excludeSwitches", [
            "enable-automation",
            "enable-logging",
            "load-extension",
            "test-type",
            "ignore-certificate-errors",
            "disable-background-networking",
            "disable-default-apps",
            "disable-extensions",
            "disable-sync",
            "disable-translate",
            "metrics-recording-only",
        ])

        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Дополнительные опции для обхода защиты
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--disable-site-isolation-trials')

        return chrome_options

    def _create_driver_with_options(self, chrome_options: ChromeOptions) -> webdriver.Chrome:
        """
        Создает драйвер с заданными опциями.
        """
        try:
            # Используем уже обновленный драйвер (не вызываем WebDriverManager.install())
            from app.services.chrome_driver_updater import ChromeDriverUpdater

            updater = ChromeDriverUpdater()
            driver_path = updater.get_driver_path()

            # Создаем сервис с явным путем к драйверу
            service = ChromeService(executable_path=driver_path)

            driver = webdriver.Chrome(service=service, options=chrome_options)

            # Настраиваем DevTools
            self._configure_devtools(driver)

            # Удаляем признаки автоматизации
            self._remove_automation_flags(driver)

            self.driver = driver
            logger.info("Chrome драйвер успешно создан")
            return driver

        except Exception as e:
            logger.error(f"Ошибка при создании Chrome драйвера: {e}")
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
                    // и другие свойства...
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
            self.driver.quit()
            self.driver = None
            logger.info("Chrome драйвер закрыт")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()