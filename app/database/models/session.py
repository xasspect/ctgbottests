# app/database/models/session.py
import uuid
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Boolean, DateTime, func, Integer, BigInteger
from app.database.models.base import Base, BaseModel


class UserSession(Base, BaseModel):
    __tablename__ = "user_sessions"

    # Для сессий используем UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # UUID как строка
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'))  # Ссылаемся на BigInteger
    category_id = Column(String, ForeignKey('categories.id'))  # Ссылаемся на String!
    purposes = Column(JSON, default=[])
    additional_params = Column(JSON, default=[])
    is_changing_params = Column(Boolean, default=False, nullable=False)
    generated_title = Column(String, nullable=True)
    keywords = Column(JSON, default=[])
    short_description = Column(String, nullable=True)
    long_description = Column(String, nullable=True)
    current_step = Column(String, default='category_selected')
    generation_mode = Column(String(50), default='advanced')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())



    # костыль
    @property
    def purpose(self):
        """Property для обратной совместимости с старым кодом"""
        try:
            # Если purposes есть и это список
            if self.purposes and isinstance(self.purposes, list) and len(self.purposes) > 0:
                first_item = self.purposes[0]
                return str(first_item)
            return None
        except Exception:
            return None

    @purpose.setter
    def purpose(self, value):
        """Сеттер для обратной совместимости"""
        try:
            if value:
                if not self.purposes:
                    self.purposes = []
                if isinstance(self.purposes, list) and value not in self.purposes:
                    self.purposes.append(value)
        except Exception:
            pass


    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, step={self.current_step})>"