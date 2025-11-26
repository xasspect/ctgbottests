from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, func
from app.database.database import database

Base = database.Base


class BaseModel:
    """Базовая модель с общими полями для PostgreSQL"""

    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self):
        """Конвертация в словарь"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }