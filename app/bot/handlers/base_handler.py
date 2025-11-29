from abc import ABC, abstractmethod


class BaseMessageHandler(ABC):
    """Базовый класс для всех обработчиков (aiogram)"""

    def __init__(self, services: dict, repositories: dict):
        self.services = services
        self.repositories = repositories

    @abstractmethod
    async def register(self, dp):
        """Регистрация обработчика в диспетчере"""
        pass