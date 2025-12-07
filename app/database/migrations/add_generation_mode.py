# app/database/migrations/add_generation_mode.py
from app.database.database import database
from sqlalchemy import text


def add_generation_mode_column():
    """Добавляет столбец generation_mode в таблицу sessions"""
    try:
        with database.engine.connect() as conn:
            # Проверяем, существует ли уже столбец
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'sessions' AND column_name = 'generation_mode'
            """))

            if not result.fetchone():
                # Добавляем столбец
                conn.execute(text("""
                    ALTER TABLE sessions 
                    ADD COLUMN generation_mode VARCHAR(50) DEFAULT 'advanced'
                """))
                conn.commit()
                print("✅ Столбец 'generation_mode' добавлен в таблицу 'sessions'")
            else:
                print("✅ Столбец 'generation_mode' уже существует")

    except Exception as e:
        print(f"❌ Ошибка при добавлении столбца: {e}")
        raise


if __name__ == "__main__":
    add_generation_mode_column()