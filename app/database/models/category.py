from sqlalchemy import Column, String, Text, JSON, Boolean
from app.database.models.base import Base, BaseModel


class Category(Base, BaseModel):
    __tablename__ = "categories"

    id = Column(String, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    system_prompt_filter = Column(Text, nullable=True)
    system_prompt_title = Column(Text, nullable=True)
    system_prompt_description = Column(Text, nullable=True)
    allowed_keywords = Column(JSON, nullable=True)
    blocked_keywords = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"