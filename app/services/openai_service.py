# app/services/openai_service.py
import openai
from typing import List, Dict, Any
import logging
from app.config.config import config


class OpenAIService:
    """Сервис для работы с OpenAI API"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=config.api.openai_key)
        self.model = config.api.openai_model
        self.max_tokens = config.api.openai_max_tokens
        self.temperature = config.api.openai_temperature
        self.logger = logging.getLogger(__name__)

    # async def filter_keywords(self, keywords: List[str], category: str,
    #                           additional_params: List[str] = None,
    #                           system_prompt: str = None) -> List[str]:
    #     """Фильтрация ключевых слов через AI"""
    #
    #     if not system_prompt:
    #         system_prompt = f"""
    #         Ты эксперт по маркетингу и SEO. Отфильтруй список ключевых слов, оставив только:
    #         1. Релевантные для категории: {category}
    #         2. Популярные и часто используемые покупателями
    #         3. Убирай дубликаты, слишком общие и нерелевантные слова
    #         4. Максимум 15 самых важных ключей
    #
    #         Дополнительные параметры: {', '.join(additional_params) if additional_params else 'нет'}
    #
    #         Верни ТОЛЬКО список ключевых слов через запятую, без пояснений.
    #         """
    #
    #     user_prompt = f"Ключевые слова для фильтрации: {', '.join(keywords)}"
    #
    #     try:
    #         response = await self.client.chat.completions.create(
    #             model=self.model,
    #             messages=[
    #                 {"role": "system", "content": system_prompt},
    #                 {"role": "user", "content": user_prompt}
    #             ],
    #             max_tokens=self.max_tokens,
    #             temperature=self.temperature
    #         )
    #
    #         filtered_text = response.choices[0].message.content.strip()
    #         filtered_keywords = [kw.strip() for kw in filtered_text.split(',')]
    #
    #         self.logger.info(f"✅ Отфильтровано ключевых слов: {len(filtered_keywords)}")
    #         return filtered_keywords[:15]  # Ограничиваем количество
    #
    #     except Exception as e:
    #         self.logger.error(f"❌ Ошибка фильтрации ключевых слов: {e}")
    #         return keywords[:8]  # Возвращаем первые 8 в случае ошибки

    async def generate_text(self, prompt: str, system_prompt: str = None, max_tokens: int = 200,
                            temperature: float = 0.7) -> str:
        """Прямая генерация текста по промпту"""
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=30.0  # Таймаут 30 секунд
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации текста: {e}")
            return f""


    # async def validate_content(self, content: str, content_type: str,
    #                            category: str, purpose: str) -> bool:
    #     """Проверка контента на релевантность"""
    #
    #     system_prompt = f"""
    #     Проверь, соответствует ли {content_type} следующим критериям:
    #     - Релевантен категории: {category}
    #     - Соответствует назначению: {purpose}
    #     - Не содержит ошибок и некорректной информации
    #     - Адекватный и логичный текст
    #
    #     Ответь только "ДА" если все критерии выполнены, или "НЕТ" если есть проблемы.
    #     """
    #
    #     try:
    #         response = await self.client.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             messages=[
    #                 {"role": "system", "content": system_prompt},
    #                 {"role": "user", "content": content}
    #             ],
    #             max_tokens=10,
    #             temperature=0.1
    #         )
    #
    #         result = response.choices[0].message.content.strip().upper()
    #         return "ДА" in result
    #
    #     except Exception as e:
    #         self.logger.error(f"❌ Ошибка валидации контента: {e}")
    #         return True  # В случае ошибки считаем валидным