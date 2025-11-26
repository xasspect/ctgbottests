from typing import List, Optional, TypeVar, Generic
from sqlalchemy.orm import Session
from app.database.database import database

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
        with self.get_session() as session:
            return session.get(self.model_class, id)

    def get_all(self) -> List[T]:
        """Получить все записи"""
        with self.get_session() as session:
            return session.query(self.model_class).all()

    def create(self, **kwargs) -> T:
        """Создать запись"""
        session = self.get_session()
        try:
            instance = self.model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
        except Exception:
            session.rollback()
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
            return instance
        except Exception:
            session.rollback()
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
                return True
            return False
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()