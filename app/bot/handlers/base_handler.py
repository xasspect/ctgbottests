
from app.utils.logger import log
from abc import ABC, abstractmethod


class BaseMessageHandler(ABC):
    """Базовый класс для всех обработчиков"""

    def __init__(self, config, services, repositories):
        self.config = config
        self.services = services
        self.repositories = repositories

    @abstractmethod
    async def register(self, dp):
        """Регистрация обработчиков"""
        pass