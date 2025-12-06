# mpstats_downloader.py
import asyncio
import logging
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from selenium import webdriver


logger = logging.getLogger(__name__)


class ButtonClicker:
    """Класс для клика по кнопкам"""

    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver

    async def click_button(self, button_element, button_info: Dict[str, Any]) -> bool:
        """
        Клик по конкретной кнопке

        Args:
            button_element: Элемент кнопки
            button_info: Информация о кнопке

        Returns:
            True если клик успешен
        """
        try:
            logger.info(f"🖱️ Клик по кнопке {button_info.get('index')}: {button_info.get('text', '')[:30]}...")

            # Прокручиваем к кнопке
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                                       button_element)

            # Случайная пауза перед кликом (имитация человеческого поведения)
            await asyncio.sleep(random.uniform(0.5, 1.5))

            # Кликаем
            button_element.click()
            logger.info(f"✅ Клик выполнен успешно")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка при клике по кнопке {button_info.get('index')}: {e}")
            return False


class MPStatsDownloader:
    """Сервис для скачивания файлов из MPStats"""

    def __init__(self, config):
        self.config = config
        self.download_dir = Path("downloads/mpstats")
        self.download_monitor = None
        self.button_clicker = None

    async def download_files(self, driver: webdriver.Chrome, buttons_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Скачивание файлов по найденным кнопкам

        Args:
            driver: WebDriver
            buttons_info: Информация о кнопках для скачивания

        Returns:
            Dict с результатом скачивания
        """
        if not buttons_info:
            return {
                "status": "error",
                "message": "❌ Нет кнопок для скачивания",
                "downloaded_files": []
            }

        try:
            # Инициализируем компоненты
            self.button_clicker = ButtonClicker(driver)
            self.download_monitor = DownloadMonitor(str(self.download_dir))

            downloaded_files = []
            failed_clicks = []

            # Определяем, сколько кнопок обработать (максимум 3)
            buttons_to_process = min(3, len(buttons_info))
            logger.info(f"Будет обработано кнопок: {buttons_to_process} из {len(buttons_info)}")

            for i in range(buttons_to_process):
                button_info = buttons_info[i]
                button_element = button_info.get('element')

                if not button_element:
                    logger.warning(f"❌ У кнопки {button_info.get('index')} нет элемента, пропускаем")
                    continue

                # Кликаем по кнопке
                click_success = await self.button_clicker.click_button(button_element, button_info)

                if click_success:
                    # Мониторим загрузку файла
                    logger.info(f"⏳ Ожидание загрузки файла {i + 1}...")

                    # Даем время для начала загрузки
                    await asyncio.sleep(random.uniform(1, 2))

                    file_path = await self.download_monitor.wait_for_download_complete(timeout=90)

                    if file_path:
                        downloaded_files.append(file_path)
                        logger.info(f"✅ Файл {i + 1} скачан: {file_path}")
                    else:
                        logger.warning(f"❌ Файл {i + 1} не был скачан")
                        failed_clicks.append(button_info.get('index'))
                else:
                    failed_clicks.append(button_info.get('index'))
                    logger.warning(f"❌ Не удалось кликнуть по кнопке {button_info.get('index')}")

                # Пауза между кликами
                if i < buttons_to_process - 1:
                    pause_time = random.uniform(2, 4)
                    logger.info(f"⏸️ Пауза {pause_time:.1f} сек перед следующим кликом...")
                    await asyncio.sleep(pause_time)

            # Формируем результат
            if downloaded_files:
                return {
                    "status": "success",
                    "message": f"✅ Скачано {len(downloaded_files)} файлов",
                    "downloaded_files": downloaded_files,
                    "failed_clicks": failed_clicks,
                    "total_attempted": buttons_to_process
                }
            else:
                return {
                    "status": "error",
                    "message": "❌ Не удалось скачать ни одного файла",
                    "downloaded_files": [],
                    "failed_clicks": failed_clicks,
                    "total_attempted": buttons_to_process
                }

        except Exception as e:
            logger.error(f"❌ Ошибка при скачивании файлов: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Ошибка скачивания: {str(e)}",
                "downloaded_files": [],
                "failed_clicks": list(range(1, len(buttons_info) + 1))
            }

    async def download_specific_button(self, driver: webdriver.Chrome, button_index: int,
                                       buttons_info: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Скачивание файла по конкретной кнопке

        Args:
            driver: WebDriver
            button_index: Индекс кнопки (начиная с 1)
            buttons_info: Информация о кнопках

        Returns:
            Dict с результатом скачивания
        """
        if button_index < 1 or button_index > len(buttons_info):
            return {
                "status": "error",
                "message": f"❌ Недопустимый индекс кнопки: {button_index}. Допустимые значения: 1-{len(buttons_info)}"
            }

        button_info = buttons_info[button_index - 1]
        button_element = button_info.get('element')

        if not button_element:
            return {
                "status": "error",
                "message": f"❌ У кнопки {button_index} нет элемента"
            }

        try:
            # Инициализируем компоненты
            self.button_clicker = ButtonClicker(driver)
            self.download_monitor = DownloadMonitor(str(self.download_dir))

            # Кликаем по кнопке
            click_success = await self.button_clicker.click_button(button_element, button_info)

            if click_success:
                # Мониторим загрузку файла
                logger.info(f"⏳ Ожидание загрузки файла...")
                await asyncio.sleep(random.uniform(1, 2))

                file_path = await self.download_monitor.wait_for_download_complete(timeout=90)

                if file_path:
                    return {
                        "status": "success",
                        "message": f"✅ Файл успешно скачан",
                        "downloaded_files": [file_path],
                        "button_index": button_index,
                        "file_path": file_path
                    }
                else:
                    return {
                        "status": "error",
                        "message": "❌ Файл не был скачан за отведенное время",
                        "downloaded_files": [],
                        "button_index": button_index
                    }
            else:
                return {
                    "status": "error",
                    "message": f"❌ Не удалось кликнуть по кнопке {button_index}",
                    "downloaded_files": [],
                    "button_index": button_index
                }

        except Exception as e:
            logger.error(f"❌ Ошибка при скачивании файла: {e}")
            return {
                "status": "error",
                "message": f"Ошибка скачивания: {str(e)}",
                "downloaded_files": [],
                "button_index": button_index
            }