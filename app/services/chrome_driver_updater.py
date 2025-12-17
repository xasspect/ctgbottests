# app/utils/chrome_driver_updater.py
import os
import logging
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService

logger = logging.getLogger(__name__)


class ChromeDriverUpdater:
    """Сервис для одноразового обновления ChromeDriver"""

    def __init__(self):
        self.driver_path = None

    def update_once(self):
        """Обновляет ChromeDriver один раз при старте приложения"""
        try:
            # Проверяем, не обновляли ли уже
            if self.driver_path and os.path.exists(self.driver_path):
                logger.info(f"✅ ChromeDriver уже обновлен: {self.driver_path}")
                return self.driver_path

            # Отключаем логи WebDriverManager
            os.environ['WDM_LOG_LEVEL'] = '0'
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'

            # Получаем последнюю версию
            logger.info("🔍 Проверяю версию ChromeDriver...")

            # Используем ChromeDriverManager для получения пути к драйверу
            driver_path = ChromeDriverManager().install()

            self.driver_path = driver_path
            logger.info(f"✅ ChromeDriver обновлен: {driver_path}")

            return driver_path

        except Exception as e:
            logger.error(f"❌ Ошибка обновления ChromeDriver: {e}")
            raise

    def get_driver_path(self):
        """Возвращает путь к обновленному драйверу"""
        if not self.driver_path:
            return self.update_once()
        return self.driver_path