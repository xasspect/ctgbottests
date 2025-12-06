# mpstats_scraper_service.py
import asyncio
import logging
import random
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app.utils.selenium_tools.download_monitor import MPStatsDownloader
from app.utils.selenium_tools.button_controller import ButtonFinder
from app.utils.selenium_tools.driver_manager import ChromeDriverManager

logger = logging.getLogger(__name__)


class MPStatsScraperService:
    """Сервис для скрапинга MPStats с использованием stealth режима"""

    def __init__(self, config):
        self.config = config
        self.driver_manager = ChromeDriverManager
        self.driver = None
        self.download_dir = Path("downloads/mpstats")

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

    async def _login_to_mpstats(self):
        """Авторизация в MPStats"""
        logger.info("Авторизация в MPStats...")

        try:
            # Переход на страницу
            self.driver.get('https://mpstats.io/seo/keywords/expanding')
            time.sleep(random.uniform(2, 4))

            # Ожидание формы логина
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.NAME, "mpstats-login-form-name"))
            )

            # Ввод email
            email_input = self.driver.find_element(By.NAME, "mpstats-login-form-name")
            email_input.click()
            time.sleep(random.uniform(0.2, 0.5))

            email = self.config.api.mpstats_email
            for char in email:
                email_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))

            # Ввод пароля
            password_input = self.driver.find_element(By.NAME, "mpstats-login-form-password")
            password_input.click()
            time.sleep(random.uniform(0.2, 0.5))

            password = self.config.api.mpstats_pswd
            for char in password:
                password_input.send_keys(char)
                time.sleep(random.uniform(0.05, 0.1))

            # Нажатие Enter для входа
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.RETURN).perform()

            # Ожидание успешного входа
            WebDriverWait(self.driver, 30).until(
                lambda d: "expanding" in d.current_url or
                          d.find_elements(By.XPATH, "//span[text()='Запросы']")
            )

            time.sleep(random.uniform(2, 4))
            logger.info("✅ Авторизация успешна")

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
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Запросы']"))
                )

                actions = ActionChains(self.driver)
                actions.move_to_element(requests_tab).perform()
                time.sleep(random.uniform(0.3, 0.7))

                requests_tab.click()
                logger.info("✅ Кликнули на вкладку 'Запросы'")
                time.sleep(random.uniform(1, 2))

            except TimeoutException:
                # Пробуем альтернативные варианты
                requests_tabs = self.driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'Запросы') or contains(text(), 'Запрос')]"
                )

                if requests_tabs:
                    requests_tabs[0].click()
                    logger.info("✅ Кликнули на альтернативную вкладку 'Запросы'")
                else:
                    logger.warning("Вкладка 'Запросы' не найдена, продолжаем...")

            # 2. Поиск textarea
            logger.info("Поиск textarea...")

            textarea = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "textarea"))
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
            textarea.clear()
            time.sleep(random.uniform(0.5, 1))

            # Имитация человеческого ввода
            textarea.click()
            time.sleep(random.uniform(0.3, 0.6))

            # Вводим текст посимвольно с паузами
            for char in query_text:
                textarea.send_keys(char)
                time.sleep(random.uniform(0.03, 0.08))

            logger.info("✅ Textarea заполнена")

            # 5. Нажимаем Tab и Enter для отправки формы
            time.sleep(random.uniform(0.5, 1))
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.TAB).perform()
            time.sleep(random.uniform(0.2, 0.4))
            actions.send_keys(Keys.ENTER).perform()

            logger.info("✅ Форма отправлена (Tab+Enter)")

            # 6. Ждем некоторое время для обработки
            time.sleep(random.uniform(3, 5))

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
                "food": "продукты питания",
                "books": "книги",
                "sports": "спорт и отдых",
                "toys": "игрушки",
                "automotive": "автомобильные товары",
                "health": "здоровье"
            }
            category_name = category_map.get(category, category)
            parts.append(category_name)

        # 2. Назначение (очищаем от эмодзи)
        purpose = params.get('purpose', '')
        if purpose:
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