# mpstats_scraper_service.py
import asyncio
import logging
import random
import time
import re
import os
from pathlib import Path
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from app.config.mpstats_ui_config import MPSTATS_UI_CONFIG

from app.utils.selenium_tools.download_monitor import MPStatsDownloader
from app.utils.selenium_tools.button_controller import ButtonFinder
from app.utils.selenium_tools.driver_manager import ChromeDriverManager

logger = logging.getLogger(__name__)


class MPStatsScraperService:
    """Сервис для скрапинга MPStats с использованием stealth режима"""

    def __init__(self, config):
        self.config = config
        self.driver_manager = ChromeDriverManager
        self.download_dir = Path("downloads/mpstats")
        self.logger = logger
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
        logger.info("🚀 Инициализация скрапера MPStats с stealth режимом...")
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def scrape_categories(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Основной метод скрапинга: авторизация и заполнение формы

        Args:
            params: Параметры запроса от пользователя

        Returns:
            Dict с результатом выполнения
        """
        # Валидация параметров
        validation_result = self._validate_params(params)
        if not validation_result["valid"]:
            return validation_result

        try:
            # 1. Настройка драйвера
            self.driver = await self._setup_driver()

            # 2. Авторизация
            await self._login_to_mpstats()

            # 3. Заполнение формы ключевыми словами
            form_result = await self._fill_keywords_form(params)

            if form_result["success"]:
                # Возвращаем успешный результат с информацией о драйвере
                return {
                    "status": "success",
                    "message": "✅ Форма успешно заполнена",
                    "driver": self.driver,
                    "query_text": form_result["query_text"],
                    "params": params
                }
            else:
                # Закрываем драйвер при ошибке
                self.cleanup()
                return {
                    "status": "error",
                    "message": form_result.get("message", "❌ Не удалось заполнить форму")
                }

        except Exception as e:
            logger.error(f"Ошибка при скрапинге: {e}", exc_info=True)
            self.cleanup()
            return {
                "status": "error",
                "message": f"❌ Ошибка при выполнении скрапинга: {str(e)}"
            }

    def _validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидация параметров

        Args:
            params: Параметры для проверки

        Returns:
            Dict с результатом валидации
        """
        required_fields = ["category", "purpose"]

        # Проверка обязательных полей
        missing_fields = []
        for field in required_fields:
            if field not in params or not params[field]:
                missing_fields.append(field)

        if missing_fields:
            return {
                "valid": False,
                "status": "error",
                "message": f"❌ Не указаны обязательные параметры: {', '.join(missing_fields)}"
            }

        # Проверка, что все параметры пустые
        category = params.get("category", "").strip()
        purpose = self._clean_purpose_text(params.get("purpose", ""))
        additional_params = params.get("additional_params", [])

        # Если additional_params - строка, преобразуем в список
        if isinstance(additional_params, str):
            additional_params = [p.strip() for p in additional_params.split(",") if p.strip()]

        # Проверяем, что есть хотя бы один непустой параметр
        if not category and not purpose and not additional_params:
            return {
                "valid": False,
                "status": "error",
                "message": "❌ Все параметры пустые. Укажите хотя бы категорию или назначение."
            }

        return {"valid": True, "status": "success"}

    # app/services/mpstats_scraper_service.py
    # Добавляем в класс MPStatsScraperService:

    def cleanup_downloads(self):
        """Очистка временных файлов"""
        try:
            if hasattr(self, 'downloads_dir') and os.path.exists(self.downloads_dir):
                # Удаляем временные файлы
                for file in os.listdir(self.downloads_dir):
                    if file.endswith('.xlsx') or file.endswith('.json'):
                        os.remove(os.path.join(self.downloads_dir, file))
                        self.logger.info(f"Удален временный файл: {file}")
            self.logger.info("✅ Временные файлы очищены")
        except Exception as e:
            self.logger.error(f"❌ Ошибка очистки временных файлов: {e}")

    async def _setup_driver(self) -> webdriver.Chrome:
        """Настройка Chrome драйвера с stealth режимом"""
        self.driver_manager = ChromeDriverManager(
            headless=False,
            use_stealth=True
        )

        stealth_options = {
            "languages": ["ru-RU", "ru", "en-US", "en"],
            "vendor": "Google Inc.",
            "platform": "Win32",
            "webgl_vendor": "Intel Inc.",
            "renderer": "Intel Iris OpenGL Engine",
            "fix_hairline": True,
            "run_on_insecure_origins": False,
        }

        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.159 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        user_agent = random.choice(user_agents)

        driver = self.driver_manager.create_driver(
            download_dir=str(self.download_dir),
            block_videos=True,
            block_images=False,
            block_sounds=True,
            user_agent=user_agent,
            stealth_options=stealth_options
        )

        # Случайные задержки
        driver.implicitly_wait(random.uniform(2, 5))

        # Случайный размер окна
        window_sizes = [(1920, 1080), (1366, 768), (1536, 864), (1440, 900)]
        width, height = random.choice(window_sizes)
        driver.set_window_size(width, height)

        # Случайное положение окна
        driver.set_window_position(
            random.randint(0, 100),
            random.randint(0, 100)
        )

        logger.info(f"✅ Драйвер создан. Размер окна: {width}x{height}")
        return driver

    async def download_keywords_data(self, driver, params: Dict[str, Any]) -> str:
        """
        Полная последовательность действий для скачивания данных
        Возвращает путь к скачанному Excel файлу
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time

            self.logger.info("🔄 Начинаю процесс скачивания данных...")

            """
            !!!
            НЕЙРОНКА НАГЕНЕРИЛА ХУЙНИ download_keywords_data ВЫЗЫВАЕТСЯ ИЗ /app/services/data_collection_service.py
            ТАМ БЛЯТЬ НУЖНО НАНИМАТЬ ДЕТЕКТИВА ЧТОБЫ РАЗОБРАТЬСЯ ЧТО И ОТКУДА ВЫЗЫВАЕТСЯ НАХУЙ Я НЕ БУДУ ЭТИМ ЗАНИМАТЬСЯ
            БУДУЩИЙ Я (РАБ ЭТОЙ ВЕЛИКОЙ КОМПАНИИ) ИЛИ ЧЕЛОВЕК КОТОРОГО НАНЯЛИ РАЗБИРАТЬСЯ В ЭТЙ ЛЕГАСИ ХУЙНИ ДАЙ ТЕБЕ
            БОГ ЗДОРОВЬЯ
            
            олежа энвилоуп 14.12.2025 11:12
            """

            # 2. Переключение на вкладку "Слова"
            try:
                elements = driver.find_elements(
                    self.by_mapping[self.words_config["by"]],
                    self.words_config["value"]
                )
                if len(elements) > 1:
                    driver.execute_script("arguments[0].click();", elements[1])
                    self.logger.info("✅ Переключились на 'Слова'")
                    time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Не удалось переключиться на 'Слова': {e}")

            # 3. Скачивание файла (первая кнопка)
            try:
                elements = driver.find_elements(
                    self.by_mapping[self.downloads_config["by"]],
                    self.downloads_config["value"]
                )
                if len(elements) > 0:
                    driver.execute_script("arguments[0].click();", elements[0])
                    self.logger.info("✅ Кликнули на первую кнопку скачивания")
                    time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Не удалось кликнуть первую кнопку: {e}")

            # 4. Скачивание файла (вторая кнопка)
            try:
                elements = driver.find_elements(
                    self.by_mapping[self.downloads_config["by"]],
                    self.downloads_config["value"]
                )
                if len(elements) > 2:
                    driver.execute_script("arguments[0].click();", elements[2])
                    self.logger.info("✅ Кликнули на вторую кнопку скачивания")
                    time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Не удалось кликнуть вторую кнопку: {e}")

            # 5. Ожидание скачивания
            downloaded_file = await self._wait_for_download()

            if downloaded_file:
                self.logger.info(f"✅ Файл скачан: {downloaded_file}")
                return downloaded_file
            else:
                raise Exception("Не удалось скачать файл")

        except Exception as e:
            self.logger.error(f"Ошибка при скачивании: {e}")
            raise

    async def _wait_for_download(self, timeout: int = 60, check_interval: int = 1) -> str:
        """Ожидание завершения скачивания файла"""
        import time

        initial_files = set()
        if os.path.exists(self.download_dir):
            initial_files = set(os.listdir(self.download_dir))

        self.logger.info(f"⏳ Ожидаю скачивания файла...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            if os.path.exists(self.download_dir):
                current_files = set(os.listdir(self.download_dir))
                new_files = current_files - initial_files

                if new_files:
                    # Ищем .xlsx файлы
                    xlsx_files = [f for f in new_files if f.endswith('.xlsx')]

                    if xlsx_files:
                        file_path = os.path.join(self.download_dir, xlsx_files[0])

                        # Проверяем, что файл полностью скачан
                        if os.path.getsize(file_path) > 0:
                            self.logger.info(f"✅ Файл готов: {xlsx_files[0]}")
                            return file_path

            await asyncio.sleep(check_interval)

        self.logger.error("⏰ Таймаут ожидания скачивания")
        return None

    async def _login_to_mpstats(self):
        """Авторизация в MPStats"""
        logger.info("Авторизация в MPStats...")

        try:
            # Переход на страницу
            self.driver.get('https://mpstats.io/seo/keywords/expanding')
            time.sleep(random.uniform(2, 4))
            current_url = self.driver.current_url
            if current_url == 'https://mpstats.io/login':

                # Ожидание формы логина
                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.NAME, "mpstats-login-form-name"))
                )

                # Ввод email
                email_input = self.driver.find_element(
                    self.by_mapping[self.email_config["by"]],
                    self.email_config["value"]
                )
                email = self.config.api.mpstats_email
                email_input.send_keys(email)

                # Ввод пароля
                password_input = self.driver.find_element(
                    self.by_mapping[self.password_config["by"]],
                    self.password_config["value"]
                )
                password = self.config.api.mpstats_pswd
                password_input.send_keys(password)

                # Нажатие Enter для входа
                password_input.send_keys(Keys.ENTER)

                # Ожидание успешного входа
                WebDriverWait(self.driver, 30).until(
                    lambda d: "expanding" in d.current_url or
                              d.find_elements(
                                  self.by_mapping[self.requests_btn_config["by"]],
                                  self.requests_btn_config["value"]
                              )
                )

                time.sleep(random.uniform(2, 4))
                logger.info("✅ Авторизация успешна")
            elif current_url == 'https://mpstats.io/seo/keywords/expanding':
                logger.info('✅ Вход без логина при помощи chrome_profile')

        except TimeoutException as e:
            logger.error("Таймаут при авторизации")
            raise Exception(f"Таймаут при авторизации: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка при авторизации: {e}")
            raise Exception(f"Ошибка авторизации: {str(e)}")

    async def _fill_keywords_form(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Заполнение формы ключевыми словами

        Args:
            params: Параметры для заполнения

        Returns:
            Dict с результатом заполнения
        """
        try:
            # 1. Клик на вкладку "Запросы"
            logger.info("Поиск вкладки 'Запросы'...")

            try:
                requests_tab = WebDriverWait(self.driver, 15).until(
                    EC.element_to_be_clickable((self.by_mapping[self.requests_btn_config["by"]],
                                                self.requests_btn_config["value"]))
                )

                elements = self.driver.find_elements(
                    self.by_mapping[self.requests_btn_config["by"]],
                    self.requests_btn_config["value"]
                )
                elements[1].click()
                time.sleep(random.uniform(0.3, 0.7))

                # requests_tab.click()
                logger.info("✅ Кликнули на вкладку 'Запросы'")
                time.sleep(random.uniform(1, 2))

            except TimeoutException:
                # Пробуем альтернативные варианты
                requests_tabs = self.driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'Запросы') or contains(text(), 'Запрос')]"
                )

                if requests_tabs:
                    requests_tabs[1].click()
                    logger.info("✅ Кликнули на альтернативную вкладку 'Запросы'")
                else:
                    logger.warning("Вкладка 'Запросы' не найдена, продолжаем...")

            # 2. Поиск textarea
            logger.info("Поиск textarea...")

            # textarea_tab = WebDriverWait(self.driver, 15).until(
            #     EC.element_to_be_clickable((self.by_mapping[self.textarea_config["by"]],
            #                                 self.textarea_config["value"]))
            # )

            textarea = self.driver.find_element(
                self.by_mapping[self.textarea_config["by"]],
                self.textarea_config["value"]
            )

            # 3. Формирование текста из параметров
            query_text = self._build_query_text(params)
            if not query_text:
                return {
                    "success": False,
                    "message": "❌ Не удалось сформировать текст запроса из параметров"
                }

            logger.info(f"Сформирован текст запроса: '{query_text}'")

            # 4. Заполнение textarea

            textarea.send_keys(query_text)


            logger.info("✅ Textarea заполнена")
            time.sleep(3)
            # 5. Нажимаем "Подобрать запросы"
            element = self.driver.find_element(self.by_mapping[self.find_queries_btn_config["by"]],
                                               self.find_queries_btn_config["value"])
            # клик по кнопке игнорирую фокус
            self.driver.execute_script("arguments[0].click();", element)

            logger.info("✅ Форма отправлена (клик по кнопке 'Подобрать запросы')")


            # 6. Ждем некоторое время для обработки
            time.sleep(20)

            return {
                "success": True,
                "query_text": query_text,
                "message": "Форма успешно заполнена и отправлена"
            }

        except TimeoutException as e:
            logger.error(f"Таймаут при заполнении формы: {e}")
            return {
                "success": False,
                "message": f"Таймаут при заполнении формы: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Ошибка при заполнении формы: {e}")
            return {
                "success": False,
                "message": f"Ошибка при заполнении формы: {str(e)}"
            }

    def _build_query_text(self, params: Dict[str, Any]) -> str:
        """
        Формирование текста запроса из параметров

        Args:
            params: Параметры от пользователя

        Returns:
            Текст для вставки в textarea или пустая строка при ошибке
        """
        parts = []

        # 1. Категория
        category = params.get('category', '').strip()
        if category:
            # Маппинг категорий на русский
            category_map = {
                "electronics": "электроника",
                "clothing": "одежда",
                "home": "дом и сад",
                "beauty": "красота и здоровье",
                "decorative_panels": "декоративные панели",
                "soft_panels": "мягкие панели",
                "self_adhesive_wallpaper": "самоклеящиеся обои",
                "pet_panels": "ПЭТ панели",
                "baby_panels": "3D панели",
                "aprons": "фартуки",
                "3d_panels": "3D панели",
                "battens": "реечные панели"
            }
            category_name = category_map.get(category, category)
            parts.append(category_name)

        # 2. Назначение (поддерживаем оба варианта: purpose и purposes)
        purposes = params.get('purposes', [])
        purpose = params.get('purpose', '')

        # Если есть purposes (массив), используем его
        if purposes:
            if isinstance(purposes, list):
                for p in purposes[:3]:  # Берем максимум 3 назначения
                    if p and isinstance(p, str):
                        purpose_clean = self._clean_purpose_text(p)
                        if purpose_clean:
                            parts.append(purpose_clean)
            else:
                # Если это строка с разделителями
                if isinstance(purposes, str):
                    purpose_items = [p.strip() for p in purposes.split(',') if p.strip()]
                    for p in purpose_items[:3]:
                        purpose_clean = self._clean_purpose_text(p)
                        if purpose_clean:
                            parts.append(purpose_clean)
        # Или используем старый формат purpose
        elif purpose:
            purpose_clean = self._clean_purpose_text(purpose)
            if purpose_clean:
                parts.append(purpose_clean)

        # 3. Дополнительные параметры
        additional_params = params.get('additional_params', [])
        if additional_params:
            # Если это строка, разделяем по запятым
            if isinstance(additional_params, str):
                additional_params = [p.strip() for p in additional_params.split(',') if p.strip()]

            # Если это список, берем первые 3 непустых элемента
            if isinstance(additional_params, list):
                for param in additional_params[:3]:
                    if param and isinstance(param, str):
                        param_clean = param.strip()
                        if param_clean:
                            parts.append(param_clean)

        # 4. Проверяем, что есть хотя бы одна часть
        if not parts:
            logger.error("❌ Не удалось сформировать текст запроса: все параметры пустые")
            return ""

        # Объединяем все части
        query_text = " ".join(parts)

        # Ограничиваем длину
        if len(query_text) > 100:
            query_text = query_text[:97] + "..."

        return query_text

    def _clean_purpose_text(self, purpose: str) -> str:
        """
        Очистка текста назначения от эмодзи и лишних символов

        Args:
            purpose: Текст назначения

        Returns:
            Очищенный текст
        """
        if not purpose:
            return ""

        # Удаляем эмодзи и другие не-буквенно-цифровые символы (кроме пробелов)
        cleaned = re.sub(r'[^\w\s]', '', purpose).strip()

        # Если после очистки остался пустой текст, возвращаем оригинал без эмодзи
        if not cleaned:
            # Более мягкая очистка: оставляем кириллицу, латиницу, цифры и пробелы
            cleaned = re.sub(r'[^\u0400-\u04FFa-zA-Z0-9\s]', '', purpose).strip()

        return cleaned

    def cleanup(self):
        """Очистка ресурсов"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Драйвер закрыт")
            except:
                pass
            self.driver = None

        # Очистка временных файлов
        try:
            for file in self.download_dir.glob("*"):
                if file.is_file():
                    file.unlink()
            logger.info("Временные файлы очищены")
        except Exception as e:
            logger.error(f"Ошибка при очистке файлов: {e}")
