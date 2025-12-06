# mpstats_button_finder.py
import logging
import time
import random
from typing import List, Dict, Any, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logger = logging.getLogger(__name__)


class ButtonFinder:
    """Класс для поиска кнопок на странице MPStats"""

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    async def find_download_buttons(self, timeout: int = 30) -> Dict[str, Any]:
        """
        Поиск кнопок скачивания на странице

        Args:
            timeout: Таймаут ожидания

        Returns:
            Dict с информацией о найденных кнопках
        """
        try:
            logger.info("🔍 Поиск кнопок 'Скачать'...")

            # Ждем появления кнопок скачивания
            try:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Скачать')]"))
                )
            except TimeoutException:
                logger.warning("Кнопки 'Скачать' не появились в течение таймаута")

            # Ищем все кнопки с текстом "Скачать"
            download_buttons = self._find_buttons_by_text("Скачать")

            # Также ищем кнопки с английским текстом
            if not download_buttons:
                download_buttons = self._find_buttons_by_text("Download")

            # Ищем кнопки экспорта
            if not download_buttons:
                download_buttons = self._find_buttons_by_text("Экспорт")

            if not download_buttons:
                download_buttons = self._find_buttons_by_text("Export")

            # Ищем по CSS классам и атрибутам
            if not download_buttons:
                download_buttons = self._find_buttons_by_css()

            logger.info(f"✅ Найдено кнопок: {len(download_buttons)}")

            # Подготавливаем информацию о кнопках
            buttons_info = []
            for i, btn in enumerate(download_buttons, 1):
                btn_info = self._get_button_info(btn, i)
                buttons_info.append(btn_info)

            return {
                "status": "success",
                "count": len(download_buttons),
                "buttons": buttons_info,
                "message": f"Найдено {len(download_buttons)} кнопок"
            }

        except Exception as e:
            logger.error(f"❌ Ошибка при поиске кнопок: {e}")
            return {
                "status": "error",
                "count": 0,
                "buttons": [],
                "message": f"Ошибка поиска кнопок: {str(e)}"
            }

    def _find_buttons_by_text(self, text: str) -> List:
        """
        Поиск кнопок по тексту

        Args:
            text: Текст для поиска

        Returns:
            Список найденных элементов
        """
        try:
            xpath = f"//*[contains(text(), '{text}')]"
            elements = self.driver.find_elements(By.XPATH, xpath)

            # Фильтруем только видимые элементы
            visible_elements = [el for el in elements if el.is_displayed()]

            logger.info(f"По тексту '{text}' найдено элементов: {len(elements)}, видимых: {len(visible_elements)}")
            return visible_elements

        except Exception as e:
            logger.warning(f"Ошибка при поиске по тексту '{text}': {e}")
            return []

    def _find_buttons_by_css(self) -> List:
        """
        Поиск кнопок по CSS селекторам

        Returns:
            Список найденных элементов
        """
        try:
            # Различные CSS селекторы для кнопок скачивания/экспорта
            css_selectors = [
                "button[class*='download'], button[class*='export']",
                "a[href*='.xlsx'], a[href*='.csv']",
                "[class*='download-btn'], [class*='export-btn']",
                "button[aria-label*='скачать'], button[aria-label*='download']"
            ]

            all_elements = []
            for selector in css_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    visible_elements = [el for el in elements if el.is_displayed()]
                    all_elements.extend(visible_elements)
                    logger.info(f"По селектору '{selector}' найдено: {len(visible_elements)}")
                except:
                    continue

            # Убираем дубликаты
            unique_elements = []
            seen_elements = set()
            for element in all_elements:
                element_id = id(element)
                if element_id not in seen_elements:
                    seen_elements.add(element_id)
                    unique_elements.append(element)

            return unique_elements

        except Exception as e:
            logger.warning(f"Ошибка при поиске по CSS: {e}")
            return []

    def _get_button_info(self, button, index: int) -> Dict[str, Any]:
        """
        Получение информации о кнопке

        Args:
            button: Элемент кнопки
            index: Индекс кнопки

        Returns:
            Dict с информацией о кнопке
        """
        try:
            text = button.text.strip() if button.text else ""
            tag_name = button.tag_name if hasattr(button, 'tag_name') else "unknown"

            # Получаем атрибуты
            attributes = {}
            try:
                attributes['class'] = button.get_attribute('class') or ""
                attributes['id'] = button.get_attribute('id') or ""
                attributes['href'] = button.get_attribute('href') or ""
                attributes['type'] = button.get_attribute('type') or ""
            except:
                pass

            # Определяем размер и положение
            try:
                location = button.location
                size = button.size
                dimensions = {
                    'x': location['x'],
                    'y': location['y'],
                    'width': size['width'],
                    'height': size['height']
                }
            except:
                dimensions = {}

            return {
                'index': index,
                'text': text[:100],  # Ограничиваем длину текста
                'tag_name': tag_name,
                'attributes': attributes,
                'dimensions': dimensions,
                'is_enabled': button.is_enabled(),
                'is_displayed': button.is_displayed(),
                'element': button  # Ссылка на сам элемент
            }

        except Exception as e:
            logger.warning(f"Ошибка при получении информации о кнопке {index}: {e}")
            return {
                'index': index,
                'text': 'Ошибка получения информации',
                'tag_name': 'unknown',
                'attributes': {},
                'dimensions': {},
                'is_enabled': False,
                'is_displayed': False
            }

    async def wait_for_buttons(self, timeout: int = 60, poll_interval: float = 1.0) -> bool:
        """
        Ожидание появления кнопок

        Args:
            timeout: Максимальное время ожидания
            poll_interval: Интервал проверки

        Returns:
            True если кнопки появились
        """
        import time as time_module

        start_time = time_module.time()

        while time_module.time() - start_time < timeout:
            buttons = self._find_buttons_by_text("Скачать")
            if buttons:
                logger.info(f"✅ Кнопки найдены: {len(buttons)}")
                return True

            # Проверяем другие варианты
            buttons = self._find_buttons_by_text("Download")
            if buttons:
                logger.info(f"✅ Кнопки Download найдены: {len(buttons)}")
                return True

            logger.debug(f"Кнопки не найдены, ждем {poll_interval} сек...")
            time_module.sleep(poll_interval)

        logger.warning(f"❌ Кнопки не появились за {timeout} секунд")
        return False