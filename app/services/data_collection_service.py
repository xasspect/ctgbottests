# app/services/data_collection_service.py
import asyncio
import logging
import os
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from app import services
from app.config.mpstats_ui_config import MPSTATS_UI_CONFIG
from app.services.mpstats_scraper_service import MPStatsScraperService
from app.utils.keywords_processor import KeywordsProcessor


class DataCollectionService:
    """Сервис для сбора и обработки данных с MPStats"""

    def __init__(self, config, scraper_service: MPStatsScraperService, **kwargs):
        self.config = config
        self.scraper = scraper_service
        self.services = self.services = kwargs.get('services', {})
        self.logger = logging.getLogger(__name__)
        self.keywords_processor = KeywordsProcessor(
            preserve_excel=False,
            target_column="Слова"
        )

        # Пути
        self.downloads_dir = Path(config.paths.mpstats_downloads_dir)
        self.keywords_dir = Path(config.paths.keywords_dir)

    async def collect_keywords_data(
            self,
            category: str,
            purpose: Union[str, List[str]] = "",
            additional_params: List[str] = None,
            category_description: str = None
    ) -> Dict[str, Any]:
        """
        Полный цикл сбора данных:
        1. Скрапинг MPStats
        2. Скачивание Excel
        3. Обработка в JSON
        4. Формирование результата

        Args:
            category: Название категории
            purpose: Назначение товара (строка или массив строк)
            additional_params: Дополнительные параметры
            category_description: Описание категории из БД
        """
        try:
            self.logger.info(f"🚀 Начинаю сбор данных для категории: {category}")

            # ДЕБАГ: выводим все полученные параметры
            self.logger.info(f"📋 Полученные параметры:")
            self.logger.info(f"  - category: {category}")
            self.logger.info(f"  - purpose: {purpose}")
            self.logger.info(f"  - additional_params: {additional_params}")
            self.logger.info(f"  - category_description: {category_description}")

            if category_description:
                self.logger.info(f"📝 Описание категории (полное): {category_description}")
                self.logger.info(f"📝 Описание категории (первые 100 символов): {category_description[:100]}...")
            else:
                self.logger.warning("⚠️ Описание категории не получено (None или пустая строка)")

            # Нормализуем purpose: преобразуем в массив строк
            purposes_list = self._normalize_purpose(purpose)

            self.logger.info(f"🎯 Назначения: {purposes_list}")

            # 1. Подготовка параметров
            params = {
                "category": category,
                "category_description": category_description or "",  # <-- ПЕРЕДАЕМ описание!
                "purposes": purposes_list,  # Передаем как массив
                "additional_params": additional_params or []
            }

            # 2. Запуск скрапинга и скачивания Excel
            self.logger.info("🔍 Запуск скрапинга MPStats...")
            self.logger.info(f"📤 Параметры для скрапера (с описанием): {params}")

            excel_file = await self._run_scraping_and_download(params)

            if not excel_file:
                raise Exception("Не удалось скачать файл с MPStats")

            self.logger.info(f"✅ Файл скачан: {excel_file}")

            self.logger.info("🔄 Закрываю Chrome драйвер...")
            if hasattr(self.scraper, 'driver') and self.scraper.driver:
                try:
                    self.scraper.driver.quit()
                    self.scraper.driver = None
                    self.logger.info("✅ Chrome драйвер закрыт")
                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось закрыть драйвер: {e}")

            # 3. Обработка Excel в JSON
            self.logger.info("🔄 Обработка Excel файла...")
            result = await self._process_excel_file(
                excel_path=excel_file,
                category=category,
                purposes=purposes_list,
                additional_params=additional_params or [],
                category_description=category_description  # <-- Передаем описание
            )

            # 4. Очистка временных файлов
            await self._cleanup_temp_files(excel_file)

            self.logger.info(f"✅ Данные собраны. Ключевых слов: {len(result.get('keywords', []))}")

            return {
                "status": "success",
                "category": category,
                "purposes": purposes_list,
                "additional_params": additional_params or [],
                "keywords": result.get("keywords", []),
                "keywords_preview": result.get("keywords", [])[:15]
            }

        except Exception as e:
            self.logger.error(f"❌ Ошибка сбора данных: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "category": category,
                "purposes": self._normalize_purpose(purpose),
                "additional_params": additional_params or [],
                "keywords": [],
                "keywords_preview": []
            }

    def _normalize_purpose(self, purpose: Union[str, List[str], None]) -> List[str]:
        """
        Нормализует purpose в массив строк

        Args:
            purpose: Назначение (строка, массив или None)

        Returns:
            Нормализованный массив назначений
        """
        if not purpose:
            return []

        if isinstance(purpose, list):
            # Фильтруем пустые строки
            return [str(p).strip() for p in purpose if str(p).strip()]
        elif isinstance(purpose, str):
            # Если строка с разделителями, разбиваем
            if "," in purpose:
                return [p.strip() for p in purpose.split(",") if p.strip()]
            else:
                return [purpose.strip()] if purpose.strip() else []
        else:
            # Преобразуем в строку
            return [str(purpose).strip()]

    async def _cleanup_temp_files(self, excel_file: str):
        """Очистка временных файлов"""
        try:
            # Удаляем Excel файл
            if os.path.exists(excel_file):
                os.remove(excel_file)
                self.logger.info(f"🗑️ Удален временный Excel файл: {excel_file}")

            # Также можно удалить другие временные файлы, если они есть
            # Например, проверяем директорию загрузок
            if os.path.exists(self.downloads_dir):
                for file in os.listdir(self.downloads_dir):
                    file_path = os.path.join(self.downloads_dir, file)
                    if file.endswith('.crdownload') or file.endswith('.tmp'):
                        try:
                            os.remove(file_path)
                            self.logger.info(f"🗑️ Удален временный файл: {file}")
                        except Exception as e:
                            self.logger.warning(f"⚠️ Не удалось удалить временный файл {file}: {e}")

        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка при очистке временных файлов: {e}")
            # Не поднимаем исключение, т.к. это не критичная операция

    async def _run_scraping_and_download(self, params: Dict[str, Any]) -> str:
        """Запуск скрапинга и скачивания Excel файла"""
        try:
            # Инициализация скрапера
            await self.scraper.initialize_scraper()

            # Для обратной совместимости с MPStatsScraperService
            # преобразуем массив purposes в строку
            scraper_params = params.copy()

            # ДЕБАГ: выводим ВСЕ параметры перед передачей
            self.logger.info(f"📤 ПЕРЕДАЧА в скрапер. Все параметры: {scraper_params}")

            # Преобразуем purposes в строку для скрапера
            if "purposes" in scraper_params:
                purposes_list = scraper_params["purposes"]
                if isinstance(purposes_list, list) and purposes_list:
                    # Объединяем в строку для scraper_service
                    scraper_params["purpose"] = ", ".join(purposes_list)
                    self.logger.info(f"🎯 Преобразовано purposes в purpose: {scraper_params['purpose']}")
                elif purposes_list:
                    scraper_params["purpose"] = str(purposes_list)
                # Удаляем ключ purposes чтобы не было конфликта
                if "purposes" in scraper_params:
                    del scraper_params["purposes"]
                    self.logger.info("🗑️ Удален ключ purposes из параметров")

            # Проверяем, что category_description есть в параметрах
            if "category_description" in scraper_params:
                self.logger.info(f"📝 category_description в параметрах: '{scraper_params['category_description']}'")
                self.logger.info(f"📏 Длина description: {len(scraper_params['category_description'])} символов")
            else:
                self.logger.warning("⚠️ category_description отсутствует в параметрах!")

            # Запуск скрапинга
            result = await self.scraper.scrape_categories(scraper_params)

            if result.get("status") != "success":
                raise Exception(f"Ошибка скрапинга: {result.get('message')}")

            driver = result.get("driver")

            if not driver:
                raise Exception("Драйвер не инициализирован")

            # Скачивание данных
            excel_file = await self.scraper.download_keywords_data(driver, scraper_params)

            return excel_file

        except Exception as e:
            self.logger.error(f"Ошибка при скачивании файла: {e}")
            raise

    # app/services/data_collection_service.py - добавьте в конец метода _process_excel_file

    async def _process_excel_file(
            self,
            excel_path: str,
            category: str,
            purposes: List[str],
            additional_params: List[str],
            category_description: str = None,
            max_keywords: int = 25
    ) -> Dict[str, Any]:
        """Обработка Excel файла через KeywordsProcessor с GPT-фильтрацией"""
        try:
            self.logger.info(f"📝 Обработка Excel файла...")

            # Создаем обогащенный JSON
            json_path = self.keywords_processor.create_enriched_json(
                excel_path=excel_path,
                category=category,
                purpose=", ".join(purposes) if purposes else "",
                additional_params=additional_params,
                json_path=str(
                    self.keywords_dir / f"{category}_{'_'.join(purposes[:2]) if purposes else 'all'}_enriched.json")
            )

            # Загружаем данные из JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Обогащаем данные purposes (массивом)
            data["purposes"] = purposes
            data["purpose"] = ", ".join(purposes) if purposes else ""

            # Добавляем описание категории в данные
            if category_description:
                data["category_description"] = category_description
                self.logger.info(f"✅ Описание категории добавлено в JSON")

            # === GPT-ФИЛЬТРАЦИЯ КЛЮЧЕВЫХ СЛОВ ===
            self.logger.info(f"🤖 Проверяю возможность GPT-фильтрации...")

            # Получаем сервисы
            openai_service = self._get_openai_service()
            prompt_service = self._get_prompt_service()

            if openai_service and prompt_service and data.get("keywords"):
                self.logger.info(f"✅ Сервисы доступны. Запускаю GPT-фильтрацию...")

                # Создаем и используем фильтр
                try:
                    from app.utils.json_keyword_filter import JSONKeywordFilter
                    filter_processor = JSONKeywordFilter(openai_service, prompt_service)

                    # Фильтруем ключевые слова до 10 самых релевантных
                    filtered_data = await filter_processor.filter_keywords_gpt(data, max_keywords)

                    # Сохраняем результат
                    data = filtered_data
                    self.logger.info(
                        f"✅ GPT-фильтрация завершена! Оставлено {len(data.get('keywords', []))} ключевых слов")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка GPT-фильтрации: {e}")
                    data = self._simple_keyword_filter(data, max_keywords)
            else:
                self.logger.warning("⚠️ Сервисы не доступны, использую простую фильтрацию")
                data = self._simple_keyword_filter(data, max_keywords)

            # Сохраняем обновленные данные
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"✅ Финальный JSON сохранен: {json_path}")
            return data

        except Exception as e:
            self.logger.error(f"Ошибка обработки Excel файла: {e}")
            raise

    def _get_openai_service(self):
        """Получение сервиса OpenAI"""
        # Пробуем получить из self.services
        if 'openai' in self.services:
            return self.services['openai']

        # Или создадим новый
        try:
            from app.services.openai_service import OpenAIService
            return OpenAIService()
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось создать OpenAIService: {e}")
            return None

    def _get_prompt_service(self):
        """Получение сервиса промптов"""
        # Пробуем получить из self.services
        if 'prompt' in self.services:
            return self.services['prompt']

        # Или создадим новый
        try:
            from app.services.prompt_service import PromptService
            return PromptService()
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось создать PromptService: {e}")
            return None


    def _simple_keyword_filter(self, data: Dict[str, Any], max_keywords: int = 25) -> Dict[str, Any]:
        """Простая фильтрация ключевых слов без GPT"""
        if "keywords" in data and data["keywords"]:
            all_keywords = data["keywords"]
            filtered_keywords = all_keywords[:max_keywords]

            data["filtered_keywords"] = filtered_keywords
            data["original_keywords_count"] = len(all_keywords)
            data["filtered_keywords_count"] = len(filtered_keywords)
            data["filtering_method"] = "simple_top_10"
            data["all_keywords"] = all_keywords
            data["keywords"] = filtered_keywords

        return data