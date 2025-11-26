from app.config.config import config


def main():
    print("🚀 Starting MPStats Content Generator (PostgreSQL)")
    print(f"Database: {config.database.name} on {config.database.host}:{config.database.port}")

    if config.validate():
        # Запуск приложения
        pass
    else:
        print("❌ Invalid configuration, exiting...")
        exit(1)