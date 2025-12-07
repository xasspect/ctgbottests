# app/database/models/content.py
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, JSON, BigInteger
from app.database.models.base import Base, BaseModel


class GeneratedContent(Base, BaseModel):
    __tablename__ = "generated_content"

    # Для контента тоже используем UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # session_id - UUID строки
    session_id = Column(String(36), ForeignKey('user_sessions.id'), nullable=False)
    # user_id - строка (Telegram ID)
    user_id = Column(BigInteger, ForeignKey('users.id'))

    # Сгенерированный контент
    title = Column(Text, nullable=False)
    short_description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)

    # Метаданные
    category_id = Column(String, ForeignKey('categories.id'), nullable=True)
    purpose = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<GeneratedContent(id={self.id}, user_id={self.user_id})>"