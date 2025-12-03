# app/services/openai_service.py
import openai
from typing import List, Dict, Any
import logging
from app.config.config import config


class OpenAIService:
    """Сервис для работы с OpenAI API"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=config.api.openai_key)
        self.max_tokens = config.api.openai_max_tokens
        self.temperature = config.api.openai_temperature
        self.logger = logging.getLogger(__name__)

    async def filter_keywords(self, keywords: List[str], category: str,
                              additional_params: List[str] = None,
                              system_prompt: str = None) -> List[str]:
        """Фильтрация ключевых слов через AI"""

        if not system_prompt:
            system_prompt = f"""
            Ты эксперт по маркетингу и SEO. Отфильтруй список ключевых слов, оставив только:
            1. Релевантные для категории: {category}
            2. Популярные и часто используемые покупателями
            3. Убирай дубликаты, слишком общие и нерелевантные слова
            4. Максимум 15 самых важных ключей

            Дополнительные параметры: {', '.join(additional_params) if additional_params else 'нет'}

            Верни ТОЛЬКО список ключевых слов через запятую, без пояснений.
            """

        user_prompt = f"Ключевые слова для фильтрации: {', '.join(keywords)}"

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )

            filtered_text = response.choices[0].message.content.strip()
            filtered_keywords = [kw.strip() for kw in filtered_text.split(',')]

            self.logger.info(f"✅ Отфильтровано ключевых слов: {len(filtered_keywords)}")
            return filtered_keywords[:15]  # Ограничиваем количество

        except Exception as e:
            self.logger.error(f"❌ Ошибка фильтрации ключевых слов: {e}")
            return keywords[:8]  # Возвращаем первые 8 в случае ошибки

    async def generate_title(self, category: str, purpose: str,
                             keywords: List[str], additional_params: List[str] = None,
                             system_prompt: str = None) -> str:
        """Генерация заголовка через AI"""

        if not system_prompt:
            system_prompt = f"""
            Ты профессиональный копирайтер для маркетплейсов. Создай продающий заголовок товара.

            Требования:
            - Максимум 60 символов
            - Включай основные ключевые слова
            - Привлекающий внимание
            - Соответствующий категории: {category}
            - Учитывающий назначение: {purpose}
            - Без эмодзи и лишних символов

            Дополнительные параметры: {', '.join(additional_params) if additional_params else 'нет'}

            Верни ТОЛЬКО готовый заголовок, без кавычек и пояснений.
            """

        user_prompt = f"Ключевые слова: {', '.join(keywords)}"

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=100,
                temperature=0.7
            )

            title = response.choices[0].message.content.strip().strip('"\'')

            # Обрезаем до максимальной длины
            if len(title) > config.generation.max_title_length:
                title = title[:config.generation.max_title_length - 3] + "..."

            self.logger.info(f"✅ Сгенерирован заголовок: {title}")
            return title

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации заголовка: {e}")
            return f"{category} {purpose} - {', '.join(keywords[:3])}"

    async def generate_description(self, title: str, keywords: List[str],
                                   description_type: str, category: str,
                                   system_prompt: str = None) -> str:
        """Генерация описания через AI"""

        type_info = {
            "short": {"max_length": config.generation.max_short_desc_length, "purpose": "краткое описание"},
            "long": {"max_length": config.generation.max_long_desc_length, "purpose": "подробное описание"}
        }

        if not system_prompt:
            system_prompt = f"""
            Ты профессиональный копирайтер. Создай {type_info[description_type]['purpose']} для товара.

            Требования:
            - Максимум {type_info[description_type]['max_length']} символов
            - Продающий и убедительный текст
            - Естественное включение ключевых слов
            - Структурированный текст (для длинного описания - с абзацами)
            - Без эмодзи
            - Соответствует категории: {category}

            Верни ТОЛЬКО готовое описание, без пояснений.
            """

        user_prompt = f"""
        Заголовок: {title}
        Ключевые слова: {', '.join(keywords)}
        Создай {type_info[description_type]['purpose']}.
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800 if description_type == "long" else 400,
                temperature=0.7
            )

            description = response.choices[0].message.content.strip()

            # Обрезаем до максимальной длины
            max_len = type_info[description_type]['max_length']
            if len(description) > max_len:
                description = description[:max_len - 3] + "..."

            self.logger.info(f"✅ Сгенерировано {type_info[description_type]['purpose']}")
            return description

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации описания: {e}")
            return f"Описание для {title}. Ключевые особенности: {', '.join(keywords[:5])}"

    async def validate_content(self, content: str, content_type: str,
                               category: str, purpose: str) -> bool:
        """Проверка контента на релевантность"""

        system_prompt = f"""
        Проверь, соответствует ли {content_type} следующим критериям:
        - Релевантен категории: {category}
        - Соответствует назначению: {purpose}
        - Не содержит ошибок и некорректной информации
        - Адекватный и логичный текст

        Ответь только "ДА" если все критерии выполнены, или "НЕТ" если есть проблемы.
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                max_tokens=10,
                temperature=0.1
            )

            result = response.choices[0].message.content.strip().upper()
            return "ДА" in result

        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации контента: {e}")
            return True  # В случае ошибки считаем валидным