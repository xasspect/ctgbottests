from sqlalchemy import Column, String, Text, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.database.models.base import Base, BaseModel


class UserSession(Base, BaseModel):
    __tablename__ = "user_sessions"

    # Используем UUID для ID
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    category_id = Column(String, ForeignKey('categories.id'), nullable=True)

    # Данные сессии
    purpose = Column(String(255), nullable=True)
    additional_params = Column(JSON, nullable=True)
    keywords = Column(JSON, nullable=True)
    generated_title = Column(Text, nullable=True)
    short_description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)

    # Состояние сессии
    current_step = Column(String(50), default="category_selection", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, step={self.current_step})>"