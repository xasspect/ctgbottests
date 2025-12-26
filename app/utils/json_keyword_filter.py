# app/utils/json_keyword_filter.py
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import asyncio
import re

logger = logging.getLogger(__name__)


class JSONKeywordFilter:
    """Обработчик JSON файлов с фильтрацией ключевых слов через GPT"""

    def __init__(self, openai_service, prompt_service):
        """
        Инициализация обработчика

        Args:
            openai_service: Сервис для работы с OpenAI API
            prompt_service: Сервис для получения промптов
        """
        self.openai_service = openai_service
        self.prompt_service = prompt_service
        self.logger = logger

    async def filter_keywords_gpt(
            self,
            json_data: Dict[str, Any],
            max_keywords: int = 10
    ) -> Dict[str, Any]:
        """
        Фильтрация ключевых слов через GPT с использованием PromptService

        Args:
            json_data: JSON данные с ключевыми словами и метаданными
            max_keywords: Сколько ключевых слов оставить (по умолчанию 10)

        Returns:
            Обновленный JSON с отфильтрованными ключевыми словами
        """
        try:
            # Извлекаем данные из JSON
            all_keywords = json_data.get("keywords", [])
            category = json_data.get("category", "")
            purposes = json_data.get("purposes", [])
            additional_params = json_data.get("additional_params", [])
            category_description = json_data.get("category_description", "")

            self.logger.info(f"🔍 Начинаю фильтрацию ключевых слов через GPT")
            self.logger.info(f"📊 Исходно: {len(all_keywords)} ключевых слов")
            self.logger.info(f"🎯 Цель: отобрать {max_keywords} лучших")

            # Проверяем, есть ли что фильтровать
            if not all_keywords or len(all_keywords) <= max_keywords:
                self.logger.info("✅ Ключевых слов уже достаточно или их нет")
                return json_data

            # Получаем промпты из PromptService
            system_prompt, user_prompt_template = self.prompt_service.get_keywords_filter_prompt(
                category=category,
                purposes=purposes,
                additional_params=additional_params,
                category_description=category_description,
                max_keywords=max_keywords
            )

            # Подготавливаем ключевые слова для промпта (берем до 50)
            keywords_for_prompt = all_keywords[:50]
            keywords_text = ", ".join(keywords_for_prompt)

            # Заменяем плейсхолдер в промпте
            user_prompt = user_prompt_template.replace("{keywords_list}", keywords_text)

            self.logger.info("🤖 Запрашиваю фильтрацию у GPT с промптом из PromptService...")
            self.logger.debug(f"System prompt: {system_prompt[:100]}...")
            self.logger.debug(f"User prompt: {user_prompt[:200]}...")

            # Запрашиваем фильтрацию у GPT
            filtered_text = await self.openai_service.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=300,
                temperature=0.3
            )

            # Парсим результат
            filtered_keywords = self._parse_gpt_response(filtered_text, max_keywords)

            # Если GPT вернул меньше слов, добавляем лучшие из оригинальных
            if len(filtered_keywords) < max_keywords:
                self.logger.warning(f"⚠️ GPT вернул только {len(filtered_keywords)} слов, добавляю лучшие из оригинала")
                remaining = max_keywords - len(filtered_keywords)
                backup_words = all_keywords[:remaining]
                filtered_keywords.extend(backup_words)
                filtered_keywords = list(set(filtered_keywords))[:max_keywords]

            self.logger.info(f"✅ Отфильтровано ключевых слов: {len(filtered_keywords)}")
            self.logger.info(f"📋 Результат: {', '.join(filtered_keywords[:5])}...")

            # Обновляем JSON
            return self._update_json_with_filtered_data(
                json_data,
                filtered_keywords,
                all_keywords,
                max_keywords
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка фильтрации ключевых слов: {e}")
            return self._fallback_filtering(json_data, max_keywords, str(e))

    def _parse_gpt_response(self, response_text: str, max_keywords: int) -> List[str]:
        """Парсинг ответа от GPT"""
        if not response_text:
            return []

        try:
            # Очищаем ответ
            cleaned = response_text.strip()

            # Удаляем нумерацию (1., 2., и т.д.)
            cleaned = re.sub(r'\d+[\.\)]\s*', '', cleaned)

            # Удаляем кавычки и скобки
            cleaned = cleaned.replace('"', '').replace("'", "").replace('«', '').replace('»', '')

            # Разделяем по запятым, точкам с запятой или переносам строк
            keywords = []
            for part in re.split(r'[,\n;]', cleaned):
                word = part.strip()
                # Удаляем начальные и конечные символы пунктуации
                word = re.sub(r'^[^\w]+|[^\w]+$', '', word)
                if word and len(word) > 1 and len(word.split()) <= 3:  # Игнорируем слишком длинные фразы
                    keywords.append(word)
                    if len(keywords) >= max_keywords:
                        break

            return keywords[:max_keywords]

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга ответа GPT: {e}")
            return []

    def _update_json_with_filtered_data(
            self,
            json_data: Dict[str, Any],
            filtered_keywords: List[str],
            all_keywords: List[str],
            max_keywords: int
    ) -> Dict[str, Any]:
        """Обновление JSON с отфильтрованными данными"""
        import time

        json_data["filtered_keywords"] = filtered_keywords
        json_data["original_keywords_count"] = len(all_keywords)
        json_data["filtered_keywords_count"] = len(filtered_keywords)
        json_data["filtering_method"] = "gpt_3.5_turbo_marketing_filter"
        json_data["filtering_timestamp"] = time.time()

        # Сохраняем все оригинальные ключевые слова
        json_data["all_keywords"] = all_keywords

        # Основное поле теперь содержит отфильтрованные слова
        json_data["keywords"] = filtered_keywords

        # Дополнительная информация
        json_data["max_keywords_limit"] = max_keywords
        json_data["keywords_source"] = "mpstats + gpt_filter"

        return json_data

    def _fallback_filtering(
            self,
            json_data: Dict[str, Any],
            max_keywords: int,
            error_message: str = ""
    ) -> Dict[str, Any]:
        """Резервная фильтрация при ошибке GPT"""
        self.logger.warning("⚠️ Использую резервную фильтрацию (топ-N оригинальных слов)")

        all_keywords = json_data.get("keywords", [])
        filtered_keywords = all_keywords[:max_keywords]

        json_data["filtered_keywords"] = filtered_keywords
        json_data["original_keywords_count"] = len(all_keywords)
        json_data["filtered_keywords_count"] = len(filtered_keywords)
        json_data["filtering_method"] = "fallback_top_original"
        json_data["filtering_error"] = error_message
        json_data["all_keywords"] = all_keywords
        json_data["keywords"] = filtered_keywords

        return json_data

    async def process_json_file(
            self,
            json_file_path: str,
            output_path: Optional[str] = None,
            max_keywords: int = 10
    ) -> str:
        """
        Обработка JSON файла с фильтрацией ключевых слов

        Args:
            json_file_path: Путь к входному JSON файлу
            output_path: Путь для сохранения результата
            max_keywords: Сколько ключевых слов оставить

        Returns:
            Путь к обработанному JSON файлу
        """
        try:
            # Загружаем JSON
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            self.logger.info(f"📂 Загружен JSON файл: {json_file_path}")

            # Фильтруем ключевые слова
            filtered_data = await self.filter_keywords_gpt(json_data, max_keywords)

            # Определяем путь для сохранения
            if output_path is None:
                input_path = Path(json_file_path)
                output_path = str(input_path.parent / f"{input_path.stem}_filtered{input_path.suffix}")

            # Сохраняем результат
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"💾 Сохранен обработанный JSON с {len(filtered_data.get('keywords', []))} ключевыми словами: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки JSON файла: {e}")
            raise