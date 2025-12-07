from typing import List, Optional, TypeVar, Generic, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.orm.sync import update

from app.database.database import database
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Базовый репозиторий для CRUD операций"""

    def __init__(self, model_class: T):
        self.model_class = model_class

    def get_session(self) -> Session:
        """Получение сессии БД"""
        return database.get_session()

    def get_by_id(self, id: str) -> Optional[T]:
        """Получить по ID"""
        session = self.get_session()
        try:
            result = session.get(self.model_class, id)
            return result
        finally:
            session.close()

    def get_all(self) -> List[T]:
        """Получить все записи"""
        session = self.get_session()
        try:
            return session.query(self.model_class).all()
        finally:
            session.close()

    def create(self, **kwargs) -> T:
        """Создать запись"""
        session = self.get_session()
        try:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            logger.info(f"✅ Создан {self.model_class.__name__}: {instance.id}")
            return instance
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка создания {self.model_class.__name__}: {e}")
            raise
        finally:
            session.close()

    def update(self, id: str, **kwargs) -> Optional[T]:
        """Обновить запись"""
        logger.info(f"🔄 Обновление {self.model_class.__name__} {id}: {kwargs}")
        session = self.get_session()
        try:
            instance = session.get(self.model_class, id)
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
                logger.info(f"✅ {self.model_class.__name__} {id} обновлен")
            return instance
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка обновления {self.model_class.__name__} {id}: {e}")
            raise
        finally:
            session.close()

    def delete(self, id: str) -> bool:
        """Удалить запись"""
        session = self.get_session()
        try:
            instance = session.get(self.model_class, id)
            if instance:
                session.delete(instance)
                session.commit()
                logger.info(f"✅ {self.model_class.__name__} {id} удален")
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка удаления {self.model_class.__name__} {id}: {e}")
            raise
        finally:
            session.close()