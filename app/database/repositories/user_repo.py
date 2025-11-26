from typing import Optional
from app.database.repositories.base import BaseRepository
from app.database.models.user import User


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        session = self.get_session()
        try:
            return session.query(User).filter(User.id == telegram_id).first()
        finally:
            session.close()

    def get_or_create(self, telegram_id: int, **kwargs) -> User:
        """Получить или создать пользователя"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == telegram_id).first()
            if user:
                return user

            # Создаем нового пользователя
            user = User(id=telegram_id, **kwargs)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def increment_daily_requests(self, telegram_id: int) -> Optional[User]:
        """Увеличить счетчик дневных запросов"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.id == telegram_id).first()
            if user:
                user.daily_requests += 1
                session.commit()
                session.refresh(user)
            return user
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()