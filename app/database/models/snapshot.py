# app/database/models/snapshot.py
import uuid
from sqlalchemy import Column, String, Text, JSON, BigInteger, DateTime, func
from app.database.models.base import Base, BaseModel


class ContentSnapshot(Base, BaseModel):
    """
    Модель для хранения снимков каждой генерации контента
    Каждая запись неизменяема и хранит полный контекст генерации
    """
    __tablename__ = "content_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, nullable=False, index=True)  # Telegram ID пользователя
    session_id = Column(String(36), nullable=True, index=True)  # ID сессии (опционально)

    # Входные данные (контекст генерации)
    category_id = Column(String, nullable=False)
    category_name = Column(String, nullable=False)
    purposes = Column(JSON, nullable=False, default=[])
    additional_params = Column(JSON, nullable=False, default=[])
    keywords = Column(JSON, nullable=False, default=[])

    # Сгенерированный контент
    wb_title = Column(Text, nullable=True)
    wb_short_desc = Column(Text, nullable=True)
    wb_long_desc = Column(Text, nullable=True)
    ozon_title = Column(Text, nullable=True)
    ozon_desc = Column(Text, nullable=True)

    # Метаданные
    generation_type = Column(String, nullable=False)  # title, short_desc, long_desc, desc
    marketplace = Column(String, nullable=False)  # wb, ozon
    created_at = Column(DateTime, default=func.now(), nullable=False)

    def __repr__(self):
        return f"<ContentSnapshot(id={self.id}, user_id={self.user_id}, created_at={self.created_at})>"