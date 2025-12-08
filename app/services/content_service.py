# app/services/content_service.py
import asyncio
import logging
from typing import List, Dict, Any
from app.services.mpstats_service import MPStatsService
from app.services.openai_service import OpenAIService


class ContentService:
    """Основной сервис для генерации контента"""

    def __init__(self, mpstats_service: MPStatsService, openai_service: OpenAIService):
        self.mpstats = mpstats_service
        self.openai = openai_service
        self.logger = logging.getLogger(__name__)

    async def generate_content_workflow(self, category_name: str, purpose: str,
                                        additional_params: List[str] = None,
                                        category_data: Dict = None) -> Dict[str, Any]:
        """Полный workflow генерации контента"""

        self.logger.info(f"🚀 Запуск генерации для {category_name} - {purpose}")

        # 1. Получение ключевых слов из MPStats
        keywords = await self.mpstats.get_keywords_by_category(category_name, purpose)

        if not keywords:
            raise Exception("Не удалось получить ключевые слова")

        # 2. Фильтрация ключевых слов
        system_prompt_filter = category_data.get('system_prompt_filter') if category_data else None
        filtered_keywords = await self.openai.filter_keywords(
            keywords, category_name, additional_params, system_prompt_filter
        )

        # 3. Генерация заголовка
        system_prompt_title = category_data.get('system_prompt_title') if category_data else None
        title = await self.openai.generate_title(
            category_name, purpose, filtered_keywords, additional_params, system_prompt_title
        )

        # 4. Валидация заголовка
        title_valid = await self.openai.validate_content(title, "заголовок", category_name, purpose)

        if not title_valid:
            self.logger.warning("⚠️ Заголовок не прошел валидацию, пробуем еще раз")
            title = await self.openai.generate_title(
                category_name, purpose, filtered_keywords, additional_params, system_prompt_title
            )

        return {
            "keywords": filtered_keywords,
            "title": title,
            "category": category_name,
            "purpose": purpose,
            "additional_params": additional_params or []
        }

    # app/services/content_service.py
    async def generate_simple_content(self, category_name: str, purpose: str, additional_params: list) -> dict:
        """Простая генерация контента без MPStats"""
        try:
            # Генерация заголовка
            title_prompt = f"""
            Создай продающий заголовок для товара на маркетплейсе.
            Категория: {category_name}
            Назначение: {purpose}
            Дополнительные параметры: {', '.join(additional_params) if additional_params else 'нет'}

            Заголовок должен быть:
            1. Продающим и привлекательным
            2. Включать основные ключевые слова
            3. Длиной 5-10 слов
            4. Без HTML тегов
            """

            title = await self.openai.generate_text(title_prompt)

            # Генерация ключевых слов
            keywords_prompt = f"""
            Извлеки 10 ключевых слов из заголовка для маркетплейса:
            Заголовок: {title}

            Ключевые слова должны быть:
            1. Релевантными товару
            2. Популярными для поиска
            3. Без стоп-слов
            4. В именительном падеже
            """

            keywords_text = await self.openai.generate_text(keywords_prompt)
            keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]

            return {
                'title': title.strip(),
                'keywords': keywords[:10],
                'description': ''
            }

        except Exception as e:
            self.logger.error(f"Error in simple generation: {e}")
            return {
                'title': f"Товар {category_name} для {purpose}",
                'keywords': [category_name, purpose],
                'description': ''
            }

    async def generate_description_workflow(self, title: str, keywords: List[str],
                                            description_type: str, category: str,
                                            category_data: Dict = None) -> str:
        """Workflow генерации описания"""

        system_prompt_desc = category_data.get('system_prompt_description') if category_data else None
        description = await self.openai.generate_description(
            title, keywords, description_type, category, system_prompt_desc
        )

        # Валидация описания
        desc_valid = await self.openai.validate_content(
            description, f"{description_type} описание", category, "товар"
        )

        if not desc_valid:
            self.logger.warning(f"❌ {description_type} описание не прошло валидацию")
            description = await self.openai.generate_description(
                title, keywords, description_type, category, system_prompt_desc
            )

        return description