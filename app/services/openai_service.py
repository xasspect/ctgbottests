# app/services/openai_service.py
import openai
from typing import List, Dict, Any, Optional
import time
from app.config.config import config
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class OpenAIService:
    """Сервис для работы с OpenAI API"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=config.api.openai_key)
        self.model = config.api.openai_model
        self.max_tokens = config.api.openai_max_tokens
        self.temperature = config.api.openai_temperature

    async def generate_text(
            self,
            prompt: str,
            system_prompt: str = None,
            max_tokens: int = None,
            temperature: float = None
    ) -> str:
        """
        Генерация текста через OpenAI API

        Args:
            prompt: Пользовательский промпт
            system_prompt: Системный промпт (опционально)
            max_tokens: Максимальное количество токенов
            temperature: Температура генерации

        Returns:
            Сгенерированный текст
        """
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            start_time = time.time()
            log.info(LogCodes.GPT_START, type=f"model={self.model}")
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                timeout=30.0
            )

            elapsed = time.time() - start_time
            log.info(LogCodes.GPT_SUCCESS, time=f"{elapsed:.1f}")

            return response.choices[0].message.content.strip()

        except openai.APIConnectionError as e:
            log.error(LogCodes.ERR_OPENAI, error=f"Connection error: {e}")
            raise
        except openai.RateLimitError as e:
            log.error(LogCodes.ERR_OPENAI, error=f"Rate limit: {e}")
            raise
        except openai.APIError as e:
            log.error(LogCodes.ERR_OPENAI, error=f"API error: {e}")
            raise
        except Exception as e:
            log.error(LogCodes.ERR_OPENAI, error=str(e))
            raise