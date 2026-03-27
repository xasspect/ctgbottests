# app/utils/json_keyword_filter.py
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import asyncio
import re
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class JSONKeywordFilter:
    """Обработчик JSON файлов с фильтрацией ключевых слов через GPT"""

    def __init__(self, openai_service, prompt_service):
        self.openai_service = openai_service
        self.prompt_service = prompt_service

    async def filter_keywords_gpt(
            self,
            json_data: Dict[str, Any],
            max_keywords: int = 25
    ) -> Dict[str, Any]:
        """Фильтрация ключевых слов через GPT"""
        try:
            all_keywords = json_data.get("keywords", [])
            category = json_data.get("category", "")
            purposes = json_data.get("purposes", [])
            additional_params = json_data.get("additional_params", [])
            category_description = json_data.get("category_description", "")

            if not all_keywords or len(all_keywords) <= max_keywords:
                return json_data

            system_prompt, user_prompt_template = self.prompt_service.get_keywords_filter_prompt(
                category=category,
                purposes=purposes,
                additional_params=additional_params,
                category_description=category_description,
                max_keywords=max_keywords
            )

            keywords_for_prompt = all_keywords[:50]
            keywords_text = ", ".join(keywords_for_prompt)

            user_prompt = user_prompt_template.replace("{keywords_list}", keywords_text)

            filtered_text = await self.openai_service.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=300,
                temperature=0.3
            )

            filtered_keywords = self._parse_gpt_response(filtered_text, max_keywords)

            if len(filtered_keywords) < max_keywords:
                remaining = max_keywords - len(filtered_keywords)
                backup_words = all_keywords[:remaining]
                filtered_keywords.extend(backup_words)
                filtered_keywords = list(set(filtered_keywords))[:max_keywords]

            return self._update_json_with_filtered_data(
                json_data,
                filtered_keywords,
                all_keywords,
                max_keywords
            )

        except Exception as e:
            log.error(LogCodes.ERR_OPENAI, error=f"Keyword filter: {e}")
            return self._fallback_filtering(json_data, max_keywords, str(e))

    def _parse_gpt_response(self, response_text: str, max_keywords: int) -> List[str]:
        """Парсинг ответа от GPT"""
        if not response_text:
            return []

        try:
            cleaned = response_text.strip()
            cleaned = re.sub(r'\d+[\.\)]\s*', '', cleaned)
            cleaned = cleaned.replace('"', '').replace("'", "").replace('«', '').replace('»', '')

            keywords = []
            for part in re.split(r'[,\n;]', cleaned):
                word = part.strip()
                word = re.sub(r'^[^\w]+|[^\w]+$', '', word)
                if word and len(word) > 1 and len(word.split()) <= 3:
                    keywords.append(word)
                    if len(keywords) >= max_keywords:
                        break

            return keywords[:max_keywords]

        except Exception as e:
            log.warning(LogCodes.ERR_PARSE, data=f"GPT response: {e}")
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
        json_data["filtering_method"] = "gpt_filter"
        json_data["filtering_timestamp"] = time.time()
        json_data["all_keywords"] = all_keywords
        json_data["keywords"] = filtered_keywords
        json_data["max_keywords_limit"] = max_keywords

        return json_data

    def _fallback_filtering(
            self,
            json_data: Dict[str, Any],
            max_keywords: int,
            error_message: str = ""
    ) -> Dict[str, Any]:
        """Резервная фильтрация при ошибке GPT"""
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
        """Обработка JSON файла с фильтрацией ключевых слов"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)

            filtered_data = await self.filter_keywords_gpt(json_data, max_keywords)

            if output_path is None:
                input_path = Path(json_file_path)
                output_path = str(input_path.parent / f"{input_path.stem}_filtered{input_path.suffix}")

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_data, f, ensure_ascii=False, indent=2)

            return output_path

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Process JSON: {e}")
            raise