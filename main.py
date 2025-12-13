#!/usr/bin/env python3
"""
Точка входа для Telegram бота (aiogram версия)
"""

import asyncio
import logging
from app.config.config import config
from app.bot.bot import ContentGeneratorBot
from app.utils.logger import setup_logging
 

async def main():
    """Основная асинхронная функция""" 
    setup_logging()
    logger = logging.getLogger(__name__)

    bot = ContentGeneratorBot(config)

    try:
        logger.info("Starting MPStats Content Generator Bot")
        await bot.initialize()
        await bot.run()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())