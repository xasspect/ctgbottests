# app/database/models/session.py
import uuid
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Boolean, DateTime, func, Integer, BigInteger
from app.database.models.base import Base, BaseModel


class UserSession(Base, BaseModel):
    __tablename__ = "user_sessions"

    # Для сессий используем UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # UUID как строка
    user_id = Column(BigInteger, ForeignKey('users.id'))  # Ссылаемся на BigInteger
    category_id = Column(String, ForeignKey('categories.id'))  # Ссылаемся на String!
    purpose = Column(String, nullable=True)
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

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, step={self.current_step})>"