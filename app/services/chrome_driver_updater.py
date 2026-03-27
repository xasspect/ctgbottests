# app/utils/chrome_driver_updater.py
import os
from webdriver_manager.chrome import ChromeDriverManager
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class ChromeDriverUpdater:
    """Сервис для одноразового обновления ChromeDriver"""

    def __init__(self):
        self.driver_path = None

    def update_once(self):
        """Обновляет ChromeDriver один раз при старте приложения"""
        try:
            if self.driver_path and os.path.exists(self.driver_path):
                log.info(LogCodes.SYS_INIT, module=f"ChromeDriver (cached: {self.driver_path})")
                return self.driver_path

            os.environ['WDM_LOG_LEVEL'] = '0'
            os.environ['WDM_PRINT_FIRST_LINE'] = 'False'

            log.info(LogCodes.SCR_DRIVER_INIT)
            driver_path = ChromeDriverManager().install()

            self.driver_path = driver_path
            log.info(LogCodes.SYS_INIT, module=f"ChromeDriver updated: {driver_path}")

            return driver_path

        except Exception as e:
            log.error(LogCodes.SCR_ERROR, error=f"ChromeDriver update: {e}")
            raise

    def get_driver_path(self):
        """Возвращает путь к обновленному драйверу"""
        if not self.driver_path:
            return self.update_once()
        return self.driver_path