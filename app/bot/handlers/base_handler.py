# app/bot/handlers/base_handler.py
import logging
from abc import ABC, abstractmethod


class BaseMessageHandler(ABC):
    """Базовый класс для всех обработчиков"""

    def __init__(self, config, services, repositories):
        self.config = config
        self.services = services
        self.repositories = repositories
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def register(self, dp):
        """Регистрация обработчиков"""
        pass