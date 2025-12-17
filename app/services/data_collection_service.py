# app/services/data_collection_service.py
import asyncio
import logging
import os
import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from app.config.mpstats_ui_config import MPSTATS_UI_CONFIG
from app.services.mpstats_scraper_service import MPStatsScraperService
from app.utils.keywords_processor import KeywordsProcessor


class DataCollectionService:
    """Сервис для сбора и обработки данных с MPStats"""

    def __init__(self, config, scraper_service: MPStatsScraperService):
        self.config = config
        self.scraper = scraper_service
        self.logger = logging.getLogger(__name__)
        self.keywords_processor = KeywordsProcessor(
            preserve_excel=False,
            target_column="Кластер WB"
        )

        # Пути
        self.downloads_dir = Path(config.paths.mpstats_downloads_dir)
        self.keywords_dir = Path(config.paths.keywords_dir)

    async def collect_keywords_data(
            self,
            category: str,
            purpose: Union[str, List[str]] = "",
            additional_params: List[str] = None
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
        """
        try:
            self.logger.info(f"🚀 Начинаю сбор данных для категории: {category}")

            # Нормализуем purpose: преобразуем в массив строк
            purposes_list = self._normalize_purpose(purpose)

            self.logger.info(f"🎯 Назначения: {purposes_list}")

            # 1. Подготовка параметров
            params = {
                "category": category,
                "purposes": purposes_list,  # Передаем как массив
                "additional_params": additional_params or []
            }

            # 2. Запуск скрапинга и скачивания Excel
            self.logger.info("🔍 Запуск скрапинга MPStats...")
            excel_file = await self._run_scraping_and_download(params)

            if not excel_file:
                raise Exception("Не удалось скачать файл с MPStats")

            self.logger.info(f"✅ Файл скачан: {excel_file}")

            # 3. Обработка Excel в JSON
            self.logger.info("🔄 Обработка Excel файла...")
            result = await self._process_excel_file(
                excel_path=excel_file,
                category=category,
                purposes=purposes_list,
                additional_params=additional_params or []
            )

            # 4. Очистка временных файлов
            await self._cleanup_temp_files(excel_file)

            self.logger.info(f"✅ Данные собраны. Ключевых слов: {len(result.get('keywords', []))}")

            return {
                "status": "success",
                "category": category,
                "purposes": purposes_list,  # Возвращаем как массив
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

    async def _run_scraping_and_download(self, params: Dict[str, Any]) -> str:
        """Запуск скрапинга и скачивания Excel файла"""
        try:
            # Инициализация скрапера
            await self.scraper.initialize_scraper()

            # Для обратной совместимости с MPStatsScraperService
            # преобразуем массив purposes в строку
            scraper_params = params.copy()
            if "purposes" in scraper_params:
                purposes_list = scraper_params["purposes"]
                if isinstance(purposes_list, list) and purposes_list:
                    # Объединяем в строку для scraper_service
                    scraper_params["purpose"] = ", ".join(purposes_list)
                elif purposes_list:
                    scraper_params["purpose"] = str(purposes_list)

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

    async def _process_excel_file(
            self,
            excel_path: str,
            category: str,
            purposes: List[str],
            additional_params: List[str]
    ) -> Dict[str, Any]:
        """Обработка Excel файла через KeywordsProcessor"""
        try:
            # Создаем обогащенный JSON
            json_path = self.keywords_processor.create_enriched_json(
                excel_path=excel_path,
                category=category,
                purpose=", ".join(purposes) if purposes else "",  # Для обратной совместимости
                additional_params=additional_params,
                json_path=str(
                    self.keywords_dir / f"{category}_{'_'.join(purposes[:2]) if purposes else 'all'}_enriched.json")
            )

            # Загружаем данные из JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Обогащаем данные purposes (массивом)
            data["purposes"] = purposes
            data["purpose"] = ", ".join(purposes) if purposes else ""  # Для обратной совместимости

            # Сохраняем обновленные данные
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return data

        except Exception as e:
            self.logger.error(f"Ошибка обработки Excel файла: {e}")
            raise

    async def _cleanup_temp_files(self, excel_file: str):
        """Очистка временных файлов"""
        try:
            if os.path.exists(excel_file):
                os.remove(excel_file)
                self.logger.info(f"🗑️ Удален временный файл: {excel_file}")
        except Exception as e:
            self.logger.warning(f"Не удалось удалить файл {excel_file}: {e}")