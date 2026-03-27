# app/utils/selenium_tools/driver_manager.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.common.exceptions import TimeoutException
import os
import logging
from typing import Optional
from app.services.chrome_driver_updater import ChromeDriverUpdater
from app.config.config import config
from app.utils.logger import log
from app.utils.log_codes import LogCodes

try:
    from selenium_stealth import stealth

    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False


class ChromeDriverManager:
    """Управление Chrome драйвером с настройками для скачивания файлов и stealth режимом"""

    def __init__(self, headless: bool = None, use_stealth: bool = None):
        self.headless = headless if headless is not None else config.selenium.headless
        self.use_stealth = use_stealth if use_stealth is not None else config.selenium.stealth_mode
        self.use_stealth = self.use_stealth and HAS_STEALTH

        self.driver = None
        self.download_dir = None
        self.last_download_dir = None
        self._initialized = False  # Флаг для одноразового логирования

        # Логируем только один раз при создании менеджера
        log.info(LogCodes.SYS_INIT,
                 module=f"ChromeDriverManager (headless={self.headless}, stealth={self.use_stealth})")

        if not self.headless:
            log.debug("Headless mode DISABLED - browser window will be visible")

    def get_downloaded_files(self, download_dir: Optional[str] = None):
        """Получает список скачанных файлов"""
        if not download_dir:
            if hasattr(self, 'last_download_dir'):
                download_dir = self.last_download_dir
            else:
                download_dir = os.path.join(os.getcwd(), 'downloads')

        if not os.path.exists(download_dir):
            return []

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
            profile_dir: Optional[str] = None,
            keep_profile: bool = True
    ) -> webdriver.Chrome:
        """Создает и настраивает Chrome драйвер"""
        import app
        app_dir = os.path.dirname(os.path.dirname(app.__file__))

        if download_dir:
            download_dir = os.path.join(app_dir, download_dir)
        else:
            download_dir = os.path.join(app_dir, 'downloads/mpstats')

        os.makedirs(download_dir, exist_ok=True)
        self.download_dir = download_dir
        self.last_download_dir = download_dir

        if profile_dir:
            user_data_dir = profile_dir
        else:
            user_data_dir = os.path.join(app_dir, 'chrome_profile')

        os.makedirs(user_data_dir, exist_ok=True)

        if keep_profile:
            log.info(LogCodes.SCR_DRIVER_INIT, extra=f"Profile: {user_data_dir}")
            if os.path.exists(os.path.join(user_data_dir, 'Default')):
                log.debug("Existing profile found")
        else:
            log.info(LogCodes.SCR_DRIVER_INIT, extra=f"Temp profile: {user_data_dir}")

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
            keep_profile=keep_profile
        )

        driver = self._create_driver_with_options(chrome_options)

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
            keep_profile: bool = True
    ) -> ChromeOptions:
        chrome_options = ChromeOptions()

        # Базовые флаги
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--remote-debugging-port=9222")

        # Headless режим (используем self.headless)
        if self.headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--log-level=3")
            log.debug("Headless mode enabled")
        else:
            log.info("[DEBUG] Headless mode DISABLED - browser window will be visible")

        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        chrome_options.add_argument("--profile-directory=Default")

        if keep_profile:
            chrome_options.add_argument("--disable-session-crashed-bubble")
            chrome_options.add_argument(
                "--disable-features=OptimizationGuideModelDownloading,OptimizationHintsFetching,OptimizationTargetPrediction,OptimizationHints")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-features=ChromeWhatsNewUI")

            prefs = {
                "credentials_enable_service": True,
                "profile.password_manager_enabled": True,
                "profile.default_content_setting_values.notifications": 2,
            }
        else:
            prefs = {}

        if not user_agent:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")

        download_prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False,
        }
        prefs.update(download_prefs)
        chrome_options.add_experimental_option("prefs", prefs)

        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        return chrome_options

    def _create_driver_with_options(self, chrome_options: ChromeOptions) -> webdriver.Chrome:
        try:
            updater = ChromeDriverUpdater()
            driver_path = updater.get_driver_path()

            if not os.path.exists(driver_path):
                log.error(LogCodes.SCR_ERROR, error=f"ChromeDriver not found at {driver_path}")
                raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")

            service = ChromeService(executable_path=driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)

            self._configure_devtools(driver)
            self._remove_automation_flags(driver)

            self.driver = driver
            log.info(LogCodes.SCR_DRIVER_INIT, extra="Chrome driver created successfully")
            return driver

        except Exception as e:
            log.error(LogCodes.SCR_ERROR, error=f"Create driver: {e}")
            raise

    def _apply_stealth_mode(self, driver: webdriver.Chrome, stealth_options: Optional[dict] = None) -> webdriver.Chrome:
        """Применяет selenium-stealth для сокрытия автоматизации"""
        if not HAS_STEALTH:
            log.warning(LogCodes.SCR_ERROR, error="selenium-stealth not installed")
            return driver

        try:
            default_options = {
                "languages": ["ru-RU", "ru", "en-US", "en"],
                "vendor": "Google Inc.",
                "platform": "Win32",
                "webgl_vendor": "Intel Inc.",
                "renderer": "Intel Iris OpenGL Engine",
                "fix_hairline": True,
                "run_on_insecure_origins": True,
            }

            options = {**default_options, **(stealth_options or {})}

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

            log.info(LogCodes.SYS_INIT, module="Stealth mode activated")
            return driver

        except Exception as e:
            log.warning(LogCodes.SCR_ERROR, error=f"Stealth mode: {e}")
            return driver

    def _remove_automation_flags(self, driver: webdriver.Chrome):
        """Удаляет флаги автоматизации"""
        try:
            driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {},
                };
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
            """)

            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false
                    });
                '''
            })

        except Exception as e:
            log.warning(LogCodes.SCR_ERROR, error=f"Remove automation flags: {e}")

    def _configure_devtools(self, driver: webdriver.Chrome):
        """Настраивает DevTools для блокировки медиа запросов"""
        try:
            driver.execute_cdp_cmd('Network.setBlockedURLs', {
                'urls': [
                    '*.mp4', '*.webm', '*.ogg', '*.avi', '*.mov', '*.wmv',
                    '*.flv', '*.mkv', '*.m4v', '*.mpg', '*.mpeg',
                    '*.3gp', '*.swf', '*.flac', '*.wav', '*.mp3',
                    '*.aac', '*.m4a', '*.gif', '*.webp', '*.apng',
                    '*.mng', '*.woff2', '*.ttf', '*.otf',
                ]
            })

            driver.execute_cdp_cmd('Network.setCacheDisabled', {
                'cacheDisabled': True
            })

        except Exception as e:
            log.warning(LogCodes.SCR_ERROR, error=f"DevTools config: {e}")

    def quit(self):
        """Закрывает драйвер"""
        if self.driver:
            try:
                self.driver.quit()
                log.info(LogCodes.SCR_DRIVER_CLOSE)
            except Exception:
                log.warning(LogCodes.SCR_ERROR, error="Failed to close driver")
            finally:
                self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.quit()