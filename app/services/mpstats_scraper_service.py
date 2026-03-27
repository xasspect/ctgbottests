# app/services/mpstats_scraper_service.py
import asyncio
import random
import time
import re
import os
from pathlib import Path
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from app.config.mpstats_ui_config import MPSTATS_UI_CONFIG
from app.config.config import config
from app.utils.selenium_tools.driver_manager import ChromeDriverManager
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class MPStatsScraperService:
    """Сервис для скрапинга MPStats с использованием stealth режима"""

    def __init__(self, config):
        self.config = config
        self.driver_manager = None
        self.download_dir = Path("downloads/mpstats")
        self.profile_dir = None
        self.driver = None

        self.email_config = MPSTATS_UI_CONFIG["login"]["email_field"]
        self.password_config = MPSTATS_UI_CONFIG["login"]["password_field"]
        self.requests_btn_config = MPSTATS_UI_CONFIG["tabs"]["requests"]
        self.words_config = MPSTATS_UI_CONFIG["tabs"]["words"]
        self.textarea_config = MPSTATS_UI_CONFIG["forms"]["textarea"]
        self.find_queries_btn_config = MPSTATS_UI_CONFIG["forms"]["find_queries_btn"]
        self.downloads_config = MPSTATS_UI_CONFIG["download"]["download_btn"]

        self.by_mapping = {
            "NAME": By.NAME,
            "ID": By.ID,
            "XPATH": By.XPATH,
            "CLASS_NAME": By.CLASS_NAME,
            "CSS_SELECTOR": By.CSS_SELECTOR,
            "TAG_NAME": By.TAG_NAME,
            "LINK_TEXT": By.LINK_TEXT,
            "PARTIAL_LINK_TEXT": By.PARTIAL_LINK_TEXT
        }

    async def initialize_scraper(self):
        """Инициализация скрапера"""
        log.info(LogCodes.SCR_DRIVER_INIT)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        import app
        app_dir = os.path.dirname(os.path.dirname(app.__file__))
        self.profile_dir = os.path.join(app_dir, 'chrome_profile')

        # Создаем driver_manager с настройками из config
        self.driver_manager = ChromeDriverManager(
            headless=config.selenium.headless,
            use_stealth=config.selenium.stealth_mode
        )

    async def scrape_categories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Основной метод скрапинга"""
        log.info(LogCodes.SCR_START)

        validation_result = self._validate_params(params)
        if not validation_result["valid"]:
            return validation_result

        try:
            self.driver = self.driver_manager.create_driver(
                download_dir=str(self.download_dir),
                profile_dir=self.profile_dir,
                keep_profile=True
            )

            await self._login_to_mpstats()

            form_result = await self._fill_keywords_form(params)

            if form_result["success"]:
                return {
                    "status": "success",
                    "message": "Форма успешно заполнена",
                    "driver": self.driver,
                    "query_text": form_result["query_text"],
                    "params": params
                }
            else:
                self.cleanup()
                return {
                    "status": "error",
                    "message": form_result.get("message", "Не удалось заполнить форму")
                }

        except Exception as e:
            log.error(LogCodes.SCR_ERROR, error=str(e))
            self.cleanup()
            return {
                "status": "error",
                "message": f"Ошибка скрапинга: {str(e)}"
            }

    def _validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация параметров"""
        required_fields = ["category", "purpose"]
        missing_fields = [f for f in required_fields if f not in params or not params[f]]

        if missing_fields:
            return {
                "valid": False,
                "status": "error",
                "message": f"Не указаны обязательные параметры: {', '.join(missing_fields)}"
            }

        return {"valid": True, "status": "success"}

    async def download_keywords_data(self, driver, params: Dict[str, Any]) -> str:
        """Скачивание данных"""
        try:
            log.info(LogCodes.SCR_DOWNLOAD_START)

            try:
                elements = driver.find_elements(
                    self.by_mapping[self.words_config["by"]],
                    self.words_config["value"]
                )
                if len(elements) > 1:
                    driver.execute_script("arguments[0].click();", elements[1])
                    time.sleep(2)
            except Exception:
                pass

            try:
                elements = driver.find_elements(
                    self.by_mapping[self.downloads_config["by"]],
                    self.downloads_config["value"]
                )
                if len(elements) > 0:
                    driver.execute_script("arguments[0].click();", elements[0])
                    time.sleep(2)
            except Exception:
                pass

            try:
                elements = driver.find_elements(
                    self.by_mapping[self.downloads_config["by"]],
                    self.downloads_config["value"]
                )
                if len(elements) > 2:
                    driver.execute_script("arguments[0].click();", elements[2])
                    time.sleep(2)
                elif len(elements) > 1:
                    driver.execute_script("arguments[0].click();", elements[1])
                    time.sleep(2)
            except Exception:
                pass

            downloaded_file = await self._wait_for_download()

            if downloaded_file:
                filename = os.path.basename(downloaded_file)
                size = os.path.getsize(downloaded_file)
                log.info(LogCodes.SCR_DOWNLOAD_COMPLETE, filename=filename, size=size)
                return downloaded_file
            else:
                raise Exception("Не удалось скачать файл")

        except Exception as e:
            log.error(LogCodes.SCR_ERROR, error=f"Download: {e}")
            raise

    async def _wait_for_download(self, timeout: int = 120, check_interval: int = 1) -> str:
        """Ожидание завершения скачивания"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not os.path.exists(self.download_dir):
                await asyncio.sleep(check_interval)
                continue

            for filename in os.listdir(self.download_dir):
                if filename.endswith('.xlsx') or filename.endswith('.xls'):
                    file_path = os.path.join(self.download_dir, filename)
                    if filename.endswith('.crdownload') or filename.endswith('.tmp'):
                        continue
                    try:
                        if os.path.getsize(file_path) > 1024:
                            return file_path
                    except OSError:
                        pass
            await asyncio.sleep(check_interval)

        return None

    async def _login_to_mpstats(self):
        """Авторизация в MPStats"""
        try:
            self.driver.get('https://mpstats.io/seo/keywords/expanding')
            time.sleep(random.uniform(2, 4))
            current_url = self.driver.current_url

            if 'https://mpstats.io/login' in current_url:
                log.info(LogCodes.SCR_LOGIN)

                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "mpstats-login-form-name"))
                )

                email_input = self.driver.find_element(
                    self.by_mapping[self.email_config["by"]],
                    self.email_config["value"]
                )
                email_input.send_keys(self.config.api.mpstats_email)

                password_input = self.driver.find_element(
                    self.by_mapping[self.password_config["by"]],
                    self.password_config["value"]
                )
                password_input.send_keys(self.config.api.mpstats_pswd)
                password_input.send_keys(Keys.ENTER)

                WebDriverWait(self.driver, 30).until(
                    lambda d: "expanding" in d.current_url
                )
                time.sleep(random.uniform(2, 4))
            elif current_url == 'https://mpstats.io/seo/keywords/expanding':
                log.info(LogCodes.SCR_LOGIN_SKIP)

        except TimeoutException:
            log.error(LogCodes.SCR_ERROR, error="Login timeout")
            raise Exception("Таймаут при авторизации")
        except Exception as e:
            log.error(LogCodes.SCR_ERROR, error=f"Login: {e}")
            raise

    async def _fill_keywords_form(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Заполнение формы ключевыми словами"""
        try:
            try:
                elements = self.driver.find_elements(
                    self.by_mapping[self.requests_btn_config["by"]],
                    self.requests_btn_config["value"]
                )
                if len(elements) > 1:
                    elements[1].click()
                else:
                    elements[0].click()
                time.sleep(random.uniform(1, 2))
            except Exception:
                pass

            textarea = self.driver.find_element(
                self.by_mapping[self.textarea_config["by"]],
                self.textarea_config["value"]
            )

            query_text = self._build_query_text(params)
            if not query_text:
                return {
                    "success": False,
                    "message": "Не удалось сформировать текст запроса"
                }

            textarea.clear()
            textarea.send_keys(query_text)
            log.info(LogCodes.SCR_FORM_FILL)
            time.sleep(3)

            element = self.driver.find_element(
                self.by_mapping[self.find_queries_btn_config["by"]],
                self.find_queries_btn_config["value"]
            )
            self.driver.execute_script("arguments[0].click();", element)

            log.info(LogCodes.SCR_WAIT, time=40)
            time.sleep(40)

            return {
                "success": True,
                "query_text": query_text,
                "message": "Форма успешно заполнена"
            }

        except Exception as e:
            log.error(LogCodes.SCR_ERROR, error=f"Form fill: {e}")
            return {
                "success": False,
                "message": f"Ошибка заполнения формы: {str(e)}"
            }

    def _build_query_text(self, params: Dict[str, Any]) -> str:
        """Формирование текста запроса"""
        parts = []

        category_description = params.get('category_description', '').strip()
        if category_description:
            parts.append(category_description)

        purpose = params.get('purpose', '')
        purpose_map = {
            "wood": "под дерево", "with_pattern": "с рисунком", "kitchen": "кухня",
            "tile": "плитка", "3d": "3D", "in_roll": "в рулоне",
            "self_adhesive": "самоклеящиеся", "stone": "под камень", "bathroom": "ванная",
            "bedroom": "спальня", "brick": "под кирпич", "marble": "под мрамор",
            "living_room": "гостиная", "white": "белый"
        }

        if purpose:
            if "," in purpose:
                purpose_items = [p.strip() for p in purpose.split(",")]
            else:
                purpose_items = [purpose.strip()]

            for p in purpose_items:
                translated = purpose_map.get(p.lower(), p)
                parts.append(translated)

        additional_params = params.get('additional_params', [])
        if additional_params:
            if isinstance(additional_params, str):
                additional_params = [p.strip() for p in additional_params.split(',')]
            for param in additional_params:
                if param and param.strip():
                    parts.append(param.strip())

        return " ".join(parts) if parts else ""

    def cleanup(self):
        """Очистка ресурсов"""
        if self.driver_manager:
            self.driver_manager.quit()
        self.driver = None