import logging
import sys
from app.config.config import config

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=getattr(logging, config.app.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot.log', encoding='utf-8')
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """Получить логгер"""
    return logging.getLogger(name)