# app/database/models/user.py
from sqlalchemy import Column, String, Integer, BigInteger
from app.database.models.base import Base, BaseModel


class User(Base, BaseModel):
    __tablename__ = "users"

    # Telegram user_id - храним как строку для единообразия
    id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(String(50), default='user')
    daily_requests = Column(Integer, default=0)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"