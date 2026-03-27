# app/database/database.py
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.config.config import config
from app.utils.logger import log
from app.utils.log_codes import LogCodes

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
            self.engine = create_engine(
                config.database.url,
                pool_size=config.database.pool_size,
                max_overflow=config.database.max_overflow,
                pool_timeout=config.database.pool_timeout,
                pool_recycle=config.database.pool_recycle,
                pool_pre_ping=True,
                echo=False  # Отключаем SQL логи
            )

            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )

            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()

            log.info(LogCodes.DB_CONNECT)

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=f"Connection failed: {e}")
            raise

    def create_tables(self):
        """Создание всех таблиц в PostgreSQL (только если их нет)"""
        try:
            from app.database.models.user import User
            from app.database.models.category import Category
            from app.database.models.session import UserSession
            from app.database.models.content import GeneratedContent
            from app.database.models.snapshot import ContentSnapshot

            # Создаем таблицы только если их нет (без удаления)
            self.Base.metadata.create_all(bind=self.engine)
            log.info(LogCodes.DB_TABLES_CREATED)

            # Проверяем и добавляем отсутствующие колонки (без generation_mode)
            self._check_and_add_missing_columns()

            # Инициализируем начальные данные (только если таблицы пустые)
            self._init_default_data()

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=f"Failed to create tables: {e}")
            raise

    def _init_default_data(self):
        """Инициализация начальных данных (только если таблицы пустые)"""
        try:
            from app.database.models.category import Category

            with self.session_scope() as session:
                existing_categories = session.query(Category).count()

                if existing_categories == 0:
                    log.info(LogCodes.SYS_INIT, module="Default categories")

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
                            name="Мягкие звукопоглощающие панели",
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
                            name="Самоклеящиеся ПЭТ панели",
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
                            name="Декоративные 3D панели малого формата",
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
                            name="Кухонные фартуки из пластика",
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
                            name="Объемные 3D панели для стен",
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
                            name="Реечные панели под дерево",
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
                    log.info(LogCodes.DB_RECORD_CREATED, table="categories", id=f"{len(default_categories)} records")
                else:
                    log.debug(f"Categories already exist: {existing_categories}")

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=f"Init data: {e}")

    def _check_and_add_missing_columns(self):
        """Проверяет и добавляет отсутствующие колонки (без generation_mode)"""
        try:
            with self.engine.connect() as conn:
                # Только необходимые колонки (убрали generation_mode)
                tables_columns = {
                    'categories': [
                        ('hidden_description', 'VARCHAR(500)', "''"),
                        ('purposes', 'JSONB', "'{}'::jsonb"),
                        ('description', 'VARCHAR(500)', "''")
                    ]
                }

                for table, columns in tables_columns.items():
                    for column_name, column_type, default_value in columns:
                        result = conn.execute(text(f"""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = '{table}' 
                            AND column_name = '{column_name}'
                        """))

                        if not result.fetchone():
                            sql = f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"
                            if default_value and default_value != "'NULL'" and default_value != "NULL":
                                sql += f" DEFAULT {default_value}"

                            conn.execute(text(sql))
                            conn.commit()
                            log.info(LogCodes.DB_MIGRATION, migration=f"Added {column_name} to {table}")

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=f"Migration: {e}")

    def get_session(self) -> Session:
        """Получение сессии БД"""
        if not self.SessionLocal:
            self.connect()
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """Контекстный менеджер для сессий"""
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
            log.info(LogCodes.DB_DISCONNECT)


database = Database()