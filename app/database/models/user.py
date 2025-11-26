from sqlalchemy import Column, BigInteger, String, Integer
from app.database.models.base import Base, BaseModel


class User(Base, BaseModel):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # Telegram user ID
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    role = Column(String(50), default="user", nullable=False)
    daily_requests = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"