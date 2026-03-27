# app/database/models/session.py (удаляем generation_mode)
import uuid
from sqlalchemy import Column, String, Text, JSON, ForeignKey, Boolean, DateTime, func, Integer, BigInteger
from app.database.models.base import Base, BaseModel


class UserSession(Base, BaseModel):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey('users.id', ondelete='CASCADE'))
    category_id = Column(String, ForeignKey('categories.id'))

    purposes = Column(JSON, default=[])
    additional_params = Column(JSON, default=[])
    keywords = Column(JSON, default=[])

    last_generated_wb_title = Column(String, nullable=True)
    last_generated_short_desc = Column(Text, nullable=True)
    last_generated_long_desc = Column(Text, nullable=True)
    last_generated_ozon_title = Column(String, nullable=True)
    last_generated_ozon_desc = Column(Text, nullable=True)

    current_step = Column(String, default='category_selected')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    @property
    def purpose(self):
        """Property для обратной совместимости"""
        try:
            if self.purposes and isinstance(self.purposes, list) and len(self.purposes) > 0:
                return str(self.purposes[0])
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