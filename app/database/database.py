# app/database/database.py
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.config.config import config

logger = logging.getLogger(__name__)


class Database:
    """Класс для управления подключением к PostgreSQL"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.Base = declarative_base()

    def connect(self):
        """Подключение к PostgreSQL"""
        try:
            # Используем настройки пула из конфигурации
            self.engine = create_engine(
                config.database.url,
                pool_size=config.database.pool_size,
                max_overflow=config.database.max_overflow,
                pool_timeout=config.database.pool_timeout,
                pool_recycle=config.database.pool_recycle,
                pool_pre_ping=True,
                echo=config.app.debug
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            # Тестируем подключение
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()

            logger.info("✅ PostgreSQL connection established")
            logger.info(f"📊 Database: {config.database.name} on {config.database.host}:{config.database.port}")

        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise

    # app/database/database.py
    # Убедитесь, что метод create_tables() работает с обновленными моделями



    def create_tables(self):
        """Создание всех таблиц в PostgreSQL"""
        try:
            from app.database.models.user import User
            from app.database.models.category import Category
            from app.database.models.session import UserSession
            from app.database.models.content import GeneratedContent

            if config.app.debug:  # Только в режиме отладки
                logger.warning("⚠️ Удаление существующих таблиц...")
                self.Base.metadata.drop_all(bind=self.engine)

            self.Base.metadata.create_all(bind=self.engine)
            logger.info("✅ PostgreSQL tables created")

            # Сначала запускаем миграции
            self._check_and_add_missing_columns()

            # Затем инициализируем начальные данные
            self._init_default_data()

        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL tables: {e}")
            raise

    def _init_default_data(self):
        """Инициализация начальных данных"""
        try:
            from app.database.models.category import Category

            with self.session_scope() as session:
                # Проверяем, есть ли уже категории
                existing_categories = session.query(Category).count()

                if existing_categories == 0:
                    logger.info("📊 Инициализация категорий по умолчанию...")

                    # Категории из вашего примера
                    default_categories = [
                        Category(
                            id="decorative_panels",
                            name="Декоративные панели",
                            hidden_description="панели ПВХ обычно 48 на 48 см",
                            description="Декоративные ПВХ панели для отделки стен",
                            purposes={
                                "kitchen": "Для кухни",
                                "bathroom": "Для ванной",
                                "tile": "Плитка",
                                "stone": "Под камень",
                                "wood": "Под дерево",
                                "white": "Белая",
                                "3d": "3Д",
                                "marble": "Под мрамор",
                                "brick": "Под кирпич",
                                "with_pattern": "С рисунком",
                                "in_roll": "В рулоне",
                                "self_adhesive": "Самоклеящиеся"
                            }
                        ),
                        Category(
                            id="soft_panels",
                            name="Мякиши",
                            hidden_description="мягкие панели нестандартных размеров",
                            description="Мягкие звукопоглощающие панели",
                            purposes={
                                "kitchen": "Для кухни",
                                "bathroom": "Для ванной",
                                "stone": "Под камень",
                                "wood": "Под дерево",
                                "white": "Белая",
                                "3d": "3Д",
                                "with_pattern": "С рисунком"
                            }
                        ),
                        Category(
                            id="self_adhesive_wallpaper",
                            name="Самоклеящиеся обои",
                            hidden_description="",
                            description="Самоклеящиеся обои для быстрой отделки",
                            purposes={
                                "kitchen": "Для кухни",
                                "bathroom": "Для ванной",
                                "tile": "Плитка",
                                "stone": "Под камень",
                                "wood": "Под дерево",
                                "white": "Белая",
                                "3d": "3Д",
                                "marble": "Под мрамор",
                                "brick": "Под кирпич",
                                "with_pattern": "С рисунком",
                                "in_roll": "В рулоне",
                                "self_adhesive": "Самоклеящиеся"
                            }
                        ),
                        Category(
                            id="pet_panels",
                            name="ПЭТы",
                            hidden_description="самоклеящиеся ПВХ панели",
                            description="Самоклеящиеся ПЭТ панели",
                            purposes={
                                "kitchen": "Для кухни",
                                "bathroom": "Для ванной",
                                "tile": "Плитка",
                                "stone": "Под камень",
                                "wood": "Под дерево",
                                "white": "Белая",
                                "marble": "Под мрамор",
                                "brick": "Под кирпич",
                                "with_pattern": "С рисунком",
                                "self_adhesive": "Самоклеящиеся"
                            }
                        ),
                        Category(
                            id="baby_panels",
                            name="Малышарики",
                            hidden_description="маленькие декоративные чаще всего 3д панели 29 на 29 см",
                            description="Декоративные 3D панели малого формата",
                            purposes={
                                "kitchen": "Для кухни",
                                "bathroom": "Для ванной",
                                "white": "Белая",
                                "3d": "3Д",
                                "with_pattern": "С рисунком"
                            }
                        ),
                        Category(
                            id="aprons",
                            name="Фартуки",
                            hidden_description="пластиковые фартуки на кухню",
                            description="Кухонные фартуки из пластика",
                            purposes={
                                "kitchen": "Для кухни",
                                "tile": "Плитка",
                                "stone": "Под камень",
                                "wood": "Под дерево",
                                "white": "Белая",
                                "3d": "3Д",
                                "marble": "Под мрамор",
                                "brick": "Под кирпич",
                                "with_pattern": "С рисунком"
                            }
                        ),
                        Category(
                            id="3d_panels",
                            name="3Д панели",
                            hidden_description="",
                            description="Объемные 3D панели для стен",
                            purposes={
                                "kitchen": "Для кухни",
                                "bathroom": "Для ванной",
                                "white": "Белая",
                                "3d": "3Д",
                                "with_pattern": "С рисунком"
                            }
                        ),
                        Category(
                            id="battens",
                            name="Рейки",
                            hidden_description="панели под дерево реечные",
                            description="Реечные панели под дерево",
                            purposes={
                                "kitchen": "Для кухни",
                                "bathroom": "Для ванной",
                                "wood": "Под дерево",
                                "white": "Белая",
                                "with_pattern": "С рисунком"
                            }
                        )
                    ]

                    for category in default_categories:
                        session.add(category)

                    session.commit()
                    logger.info(f"✅ Добавлено {len(default_categories)} категорий")
                else:
                    logger.debug(f"✅ Категории уже существуют: {existing_categories} шт")

        except Exception as e:
            logger.error(f"❌ Ошибка при инициализации данных: {e}")

    def run_migrations(self):
        """Запуск миграций базы данных"""
        try:
            # Проверяем и добавляем отсутствующие колонки
            self._check_and_add_missing_columns()
        except Exception as e:
            logger.error(f"❌ Error running migrations: {e}")

    def _check_and_add_missing_columns(self):
        """Проверяет и добавляет отсутствующие колонки"""
        try:
            with self.engine.connect() as conn:
                # Список таблиц и колонок для проверки
                tables_columns = {
                    'categories': [
                        ('hidden_description', 'VARCHAR(500)', "''"),  # ← ДОБАВЬТЕ ЭТУ СТРОКУ
                        ('purposes', 'JSONB', "'{}'::jsonb"),
                        ('description', 'VARCHAR(500)', "''")  # ← Также убедитесь, что description есть
                    ],
                    'user_sessions': [
                        ('generation_mode', 'VARCHAR(50)', "'advanced'"),
                        ('is_active', 'BOOLEAN', 'true')
                    ]
                }

                for table, columns in tables_columns.items():
                    for column_name, column_type, default_value in columns:
                        # Проверяем существование колонки
                        result = conn.execute(text(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = '{table}' 
                            AND column_name = '{column_name}'
                        """))

                        if not result.fetchone():
                            logger.info(f"🔄 Добавляю колонку '{column_name}' в таблицу '{table}'...")

                            sql = f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"
                            if default_value and default_value != "'NULL'" and default_value != "NULL":
                                sql += f" DEFAULT {default_value}"

                            conn.execute(text(sql))
                            conn.commit()

                            logger.info(f"✅ Колонка '{column_name}' добавлена в таблицу '{table}'")
                        else:
                            logger.debug(f"✅ Колонка '{column_name}' уже существует в таблице '{table}'")

        except Exception as e:
            logger.error(f"❌ Ошибка при проверке структуры БД: {e}")

    def get_session(self) -> Session:
        """Получение сессии БД"""
        if not self.SessionLocal:
            self.connect()

        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """Контекстный менеджер для сессий (для автоматического закрытия)"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Закрытие подключения к PostgreSQL"""
        if self.engine:
            self.engine.dispose()
            logger.info("✅ PostgreSQL connection closed")


# Глобальный экземпляр БД
database = Database()