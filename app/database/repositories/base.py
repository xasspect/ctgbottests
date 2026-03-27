from typing import List, Optional, TypeVar, Generic, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.orm.sync import update

from app.database.database import database
import logging

from app.utils.log_codes import LogCodes
from app.utils.logger import log

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

    # app/database/repositories/base.py

    def create(self, **kwargs) -> T:
        """Создать запись"""
        session = self.get_session()
        try:
            prepared_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, list):
                    prepared_kwargs[key] = value
                else:
                    prepared_kwargs[key] = value

            instance = self.model_class(**prepared_kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)

            # Краткий лог без деталей
            log.info(LogCodes.DB_RECORD_CREATED, table=self.model_class.__tablename__, id=instance.id[:8] if hasattr(instance, 'id') else 'new')
            return instance
        except Exception as e:
            session.rollback()
            log.error(LogCodes.ERR_DATABASE, error=str(e))
            raise
        finally:
            session.close()

    def update(self, id: str, **kwargs) -> Optional[T]:
        """Обновить запись"""
        session = self.get_session()
        try:
            instance = session.get(self.model_class, id)
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
                log.info(LogCodes.DB_RECORD_UPDATED, table=self.model_class.__tablename__, id=id[:8])
            return instance
        except Exception as e:
            session.rollback()
            log.error(LogCodes.ERR_DATABASE, error=str(e))
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
                log.info(LogCodes.DB_RECORD_DELETED, table=self.model_class.__tablename__, id=id[:8])
                return True
            return False
        except Exception as e:
            session.rollback()
            log.error(LogCodes.ERR_DATABASE, error=str(e))
            raise
        finally:
            session.close()