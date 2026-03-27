# app/utils/logger.py
import logging
import sys
from typing import Optional
from app.config.config import config
from app.utils.log_codes import LogCodes


class LogFormatter(logging.Formatter):
    """Форматтер с поддержкой кодов и сокращенных сообщений"""

    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def format(self, record):
        # Укорачиваем имена логгеров
        if record.name.startswith('app.'):
            record.name = record.name.replace('app.', '')

        # Сокращаем длинные сообщения (>300 символов)
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            if len(record.msg) > 300:
                record.msg = record.msg[:297] + '...'

        return super().format(record)


class AppLogger:
    """Единый логгер для всего приложения"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logging()
        return cls._instance

    def _setup_logging(self):
        """Настройка логирования"""
        self.logger = logging.getLogger('app')
        self.logger.setLevel(getattr(logging, config.app.log_level))

        # Очищаем существующие обработчики
        self.logger.handlers.clear()

        # Консольный обработчик (все уровни)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(LogFormatter())
        self.logger.addHandler(console_handler)

        # Файловый обработчик (только WARNING и выше)
        file_handler = logging.FileHandler(config.paths.log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(LogFormatter())
        self.logger.addHandler(file_handler)

        # Отключаем шумные логгеры
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.WARNING)
        logging.getLogger('aiogram.event').setLevel(logging.WARNING)
        logging.getLogger('aiogram.dispatcher').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('WDM').setLevel(logging.WARNING)
        logging.getLogger('selenium').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

        # Логируем запуск
        self.info(LogCodes.SYS_CONFIG)

    def info(self, code: str, *args, **kwargs):
        """Логирование информационного сообщения"""
        try:
            if args:
                message = code.format(*args, **kwargs)
            else:
                message = code.format(**kwargs) if kwargs else code
            self.logger.info(message)
        except Exception:
            # Если форматирование не удалось, выводим как есть
            self.logger.info(code)

    def warning(self, code: str, *args, **kwargs):
        """Логирование предупреждения"""
        try:
            if args:
                message = code.format(*args, **kwargs)
            else:
                message = code.format(**kwargs) if kwargs else code
            self.logger.warning(message)
        except Exception:
            self.logger.warning(code)

    def error(self, code: str, *args, **kwargs):
        """Логирование ошибки"""
        try:
            if args:
                message = code.format(*args, **kwargs)
            else:
                message = code.format(**kwargs) if kwargs else code
            self.logger.error(message)
        except Exception:
            self.logger.error(code)

    def debug(self, message: str):
        """Отладочное сообщение (только при DEBUG режиме)"""
        if config.app.debug:
            self.logger.debug(message)


# Глобальный экземпляр
log = AppLogger()


def setup_logging():
    """Настройка логирования (для обратной совместимости)"""
    return log


def get_logger(name: str) -> logging.Logger:
    """Получить стандартный логгер (для библиотек)"""
    return logging.getLogger(name)