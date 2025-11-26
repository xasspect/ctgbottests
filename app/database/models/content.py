from sqlalchemy import Column, String, Text, ForeignKey, JSON, BigInteger
from app.database.models.base import Base, BaseModel


class GeneratedContent(Base, BaseModel):
    __tablename__ = "generated_content"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey('user_sessions.id'), nullable=False)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False)

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