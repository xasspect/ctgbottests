# app/services/mpstats_service.py
import aiohttp
import asyncio
from typing import List, Dict, Any
import logging
from app.config.config import config
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class MPStatsService:
    """Сервис для работы с MPStats API (заглушка)"""

    def __init__(self):
        self.base_url = config.api.mpstats_base_url
        self.api_key = config.api.mpstats_key
        self.delay = config.api.mpstats_delay
        self.timeout = config.api.mpstats_timeout
        self.session = None

    async def get_session(self):
        """Получить или создать aiohttp сессию"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={
                    'X-MpStats-TOKEN': self.api_key,
                    'Content-Type': 'application/json'
                },
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self.session

    async def get_keywords_by_category(self, category_name: str, purpose: str) -> List[str]:
        """Получить ключевые слова по категории и назначению (заглушка)"""
        try:
            session = await self.get_session()
            await asyncio.sleep(self.delay)

            keywords = await self._get_mock_keywords(category_name, purpose)
            log.info(LogCodes.DATA_KEYWORDS_EXTRACT, count=len(keywords))
            return keywords

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Get keywords: {e}")
            return []

    # async def _get_mock_keywords(self, category: str, purpose: str) -> List[str]:
    #     """Заглушка для получения ключевых слов"""
    #     mock_data = {
    #         "electronics": {
    #             "gaming": [
    #                 "игровой смартфон", "высокая производительность", "gaming phone", "мощный процессор",
    #                 "игры без лагов", "высокий FPS", "система охлаждения", "игровой режим",
    #                 "антибликовое покрытие", "быстрый отклик", "оптимизация для игр", "игровая графика",
    #                 "емкий аккумулятор", "игры на максималках", "гейминг", "производительность"
    #             ],
    #             "everyday": [
    #                 "смартфон", "качественная камера", "долгая батарея", "надежный", "удобный",
    #                 "компактный", "стильный дизайн", "ежедневное использование", "универсальный",
    #                 "практичный", "доступный", "популярная модель", "баланс цена-качество"
    #             ],
    #         },
    #         "clothing": {
    #             "sport": [
    #                 "спортивная одежда", "дыхательные материалы", "комфорт при тренировках", "эластичная ткань",
    #                 "влагопоглощение", "спортивный костюм", "тренировочная форма", "фитнес одежда",
    #             ],
    #         },
    #         "home": {
    #             "kitchen": [
    #                 "кухонные принадлежности", "практичность", "легкость ухода", "функциональность",
    #                 "качественные материалы", "долговечность", "эргономичный дизайн", "безопасность",
    #             ],
    #         },
    #     }
    #
    #     category_keywords = mock_data.get(category, {})
    #     return category_keywords.get(purpose, ["качественный", "популярный", purpose])

    async def close(self):
        """Закрыть сессию"""
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()