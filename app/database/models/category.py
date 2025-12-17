# app/database/models/category.py
from sqlalchemy import Column, String, Text, DateTime, func, JSON
from app.database.models.base import Base, BaseModel


class Category(Base, BaseModel):
    __tablename__ = "categories"

    # Категория имеет строковый ID (например, "clothing", "electronics")
    id = Column(String, primary_key=True)  # Строковый ID категории
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    hidden_description = Column(String, nullable=True)
    system_prompt_filter = Column(Text, nullable=True)
    system_prompt_title = Column(Text, nullable=True)
    system_prompt_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    purposes = Column(JSON, nullable=True, default=dict)  # Добавляем поле для целей


    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"