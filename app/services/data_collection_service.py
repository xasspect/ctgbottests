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
from app.utils.temp_file_manager import temp_manager
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class DataCollectionService:
    """Сервис для сбора и обработки данных с MPStats"""

    def __init__(self, config, scraper_service: MPStatsScraperService, **kwargs):
        self.config = config
        self.scraper = scraper_service
        self.services = kwargs.get('services', {})
        self.keywords_processor = KeywordsProcessor(
            preserve_excel=False,
            target_column="Слова",
            auto_delete_json=True
        )

        self.downloads_dir = Path(config.paths.mpstats_downloads_dir)
        self.keywords_dir = Path(config.paths.keywords_dir)

    async def collect_keywords_data(
            self,
            category: str,
            purpose: Union[str, List[str]] = "",
            additional_params: List[str] = None,
            category_description: str = None,
            max_keywords: int = 13
    ) -> Dict[str, Any]:
        """Полный цикл сбора данных с обязательной GPT-фильтрацией"""
        try:
            log.info(LogCodes.SCR_START)

            purposes_list = self._normalize_purpose(purpose)

            params = {
                "category": category,
                "category_description": category_description or "",
                "purposes": purposes_list,
                "additional_params": additional_params or []
            }

            excel_file = await self._run_scraping_and_download(params)

            if not excel_file:
                raise Exception("Не удалось скачать файл с MPStats")

            if hasattr(self.scraper, 'driver') and self.scraper.driver:
                try:
                    self.scraper.driver.quit()
                    self.scraper.driver = None
                    log.info(LogCodes.SCR_DRIVER_CLOSE)
                except Exception as e:
                    log.warning(LogCodes.SCR_ERROR, error=f"Driver close: {e}")

            # Обрабатываем Excel и применяем GPT-фильтрацию
            filtered_data = await self._process_excel_file(
                excel_path=excel_file,
                category=category,
                purposes=purposes_list,
                additional_params=additional_params or [],
                category_description=category_description,
                max_keywords=max_keywords
            )

            await self._cleanup_temp_files(excel_file)

            log.info(LogCodes.SCR_SUCCESS)

            return {
                "status": "success",
                "category": category,
                "purposes": purposes_list,
                "additional_params": additional_params or [],
                "keywords": filtered_data.get("keywords", []),
                "keywords_preview": filtered_data.get("keywords", [])[:15]
            }

        except Exception as e:
            log.error(LogCodes.SCR_ERROR, error=str(e))
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
        """Нормализует purpose в массив строк"""
        if not purpose:
            return []

        if isinstance(purpose, list):
            return [str(p).strip() for p in purpose if str(p).strip()]
        elif isinstance(purpose, str):
            if "," in purpose:
                return [p.strip() for p in purpose.split(",") if p.strip()]
            else:
                return [purpose.strip()] if purpose.strip() else []
        else:
            return [str(purpose).strip()]

    async def _run_scraping_and_download(self, params: Dict[str, Any]) -> str:
        """Запуск скрапинга и скачивания Excel файла"""
        try:
            await self.scraper.initialize_scraper()

            scraper_params = params.copy()

            if "purposes" in scraper_params:
                purposes_list = scraper_params["purposes"]
                if isinstance(purposes_list, list) and purposes_list:
                    scraper_params["purpose"] = ", ".join(purposes_list)
                elif purposes_list:
                    scraper_params["purpose"] = str(purposes_list)
                if "purposes" in scraper_params:
                    del scraper_params["purposes"]

            result = await self.scraper.scrape_categories(scraper_params)

            if result.get("status") != "success":
                raise Exception(f"Ошибка скрапинга: {result.get('message')}")

            driver = result.get("driver")

            if not driver:
                raise Exception("Драйвер не инициализирован")

            excel_file = await self.scraper.download_keywords_data(driver, scraper_params)

            return excel_file

        except Exception as e:
            log.error(LogCodes.SCR_ERROR, error=str(e))
            raise

    async def _process_excel_file(
            self,
            excel_path: str,
            category: str,
            purposes: List[str],
            additional_params: List[str],
            category_description: str = None,
            max_keywords: int = 13
    ) -> Dict[str, Any]:
        """Обработка Excel файла через KeywordsProcessor с обязательной GPT-фильтрацией"""
        try:
            # Создаем обогащенный JSON
            json_path = self.keywords_processor.create_enriched_json(
                excel_path=excel_path,
                category=category,
                purpose=", ".join(purposes) if purposes else "",
                additional_params=additional_params,
                json_path=str(
                    self.keywords_dir / f"{category}_{'_'.join(purposes[:2]) if purposes else 'all'}_enriched.json"
                ),
                auto_delete=True
            )

            # Загружаем JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Добавляем метаданные
            data["purposes"] = purposes
            data["purpose"] = ", ".join(purposes) if purposes else ""

            if category_description:
                data["category_description"] = category_description

            # Получаем сервисы для GPT-фильтрации
            openai_service = self._get_openai_service()
            prompt_service = self._get_prompt_service()

            # Проверяем наличие ключевых слов и сервисов
            if not data.get("keywords"):
                error_msg = "No keywords found in Excel file"
                log.error(LogCodes.ERR_MPSTATS, error=error_msg)
                raise Exception(error_msg)

            if not openai_service or not prompt_service:
                error_msg = "OpenAI or Prompt service not available for keyword filtering"
                log.error(LogCodes.ERR_OPENAI, error=error_msg)
                raise Exception(error_msg)

            # Применяем GPT-фильтрацию
            from app.utils.json_keyword_filter import JSONKeywordFilter
            filter_processor = JSONKeywordFilter(openai_service, prompt_service)

            original_count = len(data.get("keywords", []))
            log.info(LogCodes.GPT_START, type="keyword_filter")

            filtered_data = await filter_processor.filter_keywords_gpt(data, max_keywords)
            filtered_count = len(filtered_data.get("keywords", []))

            # Проверяем результат фильтрации
            if filtered_count == 0:
                error_msg = f"GPT filtering returned 0 keywords (original: {original_count})"
                log.error(LogCodes.ERR_OPENAI, error=error_msg)
                raise Exception(error_msg)

            log.info(LogCodes.GPT_KEYWORD_FILTER, count=original_count, filtered=filtered_count)

            # Сохраняем отфильтрованные данные
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=2)

            # Удаляем JSON после использования
            try:
                if os.path.exists(json_path):
                    temp_manager.delete_file(json_path)
                    log.info(LogCodes.DATA_JSON_DELETE, filename=os.path.basename(json_path))
            except Exception as e:
                log.warning(LogCodes.SCR_ERROR, error=f"JSON delete: {e}")

            return filtered_data

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Process Excel: {e}")
            raise

    def _get_openai_service(self):
        """Получение сервиса OpenAI"""
        if 'openai' in self.services:
            return self.services['openai']
        try:
            from app.services.openai_service import OpenAIService
            openai_service = OpenAIService()
            log.info(LogCodes.SYS_INIT, module="OpenAIService")
            return openai_service
        except ImportError as e:
            log.error(LogCodes.ERR_OPENAI, error=f"Import error: {e}")
            return None
        except Exception as e:
            log.error(LogCodes.ERR_OPENAI, error=f"Init error: {e}")
            return None

    def _get_prompt_service(self):
        """Получение сервиса промптов"""
        if 'prompt' in self.services:
            return self.services['prompt']
        try:
            from app.services.prompt_service import PromptService
            prompt_service = PromptService()
            log.info(LogCodes.SYS_INIT, module="PromptService")
            return prompt_service
        except ImportError as e:
            log.error(LogCodes.ERR_OPENAI, error=f"Import error: {e}")
            return None
        except Exception as e:
            log.error(LogCodes.ERR_OPENAI, error=f"Init error: {e}")
            return None

    async def _cleanup_temp_files(self, excel_file: str):
        """Очистка временных файлов"""
        try:
            if os.path.exists(excel_file):
                os.remove(excel_file)
                log.info(LogCodes.DATA_JSON_DELETE, filename=os.path.basename(excel_file))
        except Exception as e:
            log.warning(LogCodes.SCR_ERROR, error=f"Cleanup: {e}")