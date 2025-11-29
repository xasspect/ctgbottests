#!/usr/bin/env python3
"""
Скрипт для обновления структуры БД
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.database import database
from app.database.models.user import User
from app.database.models.category import Category
from app.database.models.session import UserSession


def update_database():
    """Обновляет структуру БД"""
    print("🔄 Updating database structure...")

    try:
        # Подключаемся к БД
        database.connect()

        # Удаляем старые таблицы
        print("🗑️  Dropping old tables...")
        UserSession.__table__.drop(database.engine, checkfirst=True)
        User.__table__.drop(database.engine, checkfirst=True)
        Category.__table__.drop(database.engine, checkfirst=True)

        # Создаем новые таблицы
        print("📦 Creating new tables...")
        database.create_tables()

        print("✅ Database updated successfully!")

    except Exception as e:
        print(f"❌ Error updating database: {e}")
    finally:
        database.close()


if __name__ == "__main__":
    update_database()