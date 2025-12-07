# scripts/recreate_database.py
# !/usr/bin/env python3
"""Пересоздание всей базы данных с нуля"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import database
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def recreate_database():
    """Полностью пересоздать базу данных"""
    print("🔄 Удаление базы данных...")

    # Подключаемся к базе данных
    database.connect()

    try:
        with database.engine.connect() as conn:
            # Удаляем таблицы в правильном порядке (из-за foreign keys)
            print("🗑️  Удаляю таблицы...")

            # Используем CASCADE для удаления зависимостей
            conn.execute(text("DROP TABLE IF EXISTS generated_content CASCADE"))
            logger.info("✅ Таблица generated_content удалена")

            conn.execute(text("DROP TABLE IF EXISTS user_sessions CASCADE"))
            logger.info("✅ Таблица user_sessions удалена")

            conn.execute(text("DROP TABLE IF EXISTS categories CASCADE"))
            logger.info("✅ Таблица categories удалена")

            conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            logger.info("✅ Таблица users удалена")

            conn.commit()
            print("✅ Все таблицы удалены")

            # Создаем таблицы заново в стиле SQLAlchemy

            # Создаем таблицу users (со строковым id для Telegram)

    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        raise
    finally:
        database.close()


if __name__ == "__main__":
    print("=" * 60)
    print("🚨 УДАЛЕНИЕ БАЗЫ ДАННЫХ")
    print("=" * 60)
    print("⚠️  ВНИМАНИЕ: Все данные будут удалены!")
    print("=" * 60)

    response = input("Продолжить? (y/N): ")
    if response.lower() == 'y':
        recreate_database()
    else:
        print("Отмена операции")