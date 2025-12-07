# app/__init__.py
"""
MPStats Content Generator Bot
"""

__version__ = "1.0.0"

from app.bot.bot import ContentGeneratorBot
from app.config.config import Config
from app.utils.keywords_processor import KeywordsProcessor

__all__ = ['ContentGeneratorBot', 'Config', 'KeywordsProcessor']