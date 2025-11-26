from typing import List, Optional
from app.database.repositories.base import BaseRepository
from app.database.models.session import UserSession


class SessionRepository(BaseRepository[UserSession]):
    def __init__(self):
        super().__init__(UserSession)

    def get_active_session(self, user_id: int) -> Optional[UserSession]:
        """Получить активную сессию пользователя"""
        with self.get_session() as session:
            return (
                session.query(UserSession)
                .filter(
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
                .first()
            )

    def get_user_sessions(self, user_id: int) -> List[UserSession]:
        """Получить все сессии пользователя"""
        with self.get_session() as session:
            return (
                session.query(UserSession)
                .filter(UserSession.user_id == user_id)
                .order_by(UserSession.created_at.desc())
                .all()
            )

    def deactivate_all_sessions(self, user_id: int) -> None:
        """Деактивировать все сессии пользователя"""
        with self.get_session() as session:
            sessions = session.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).all()

            for user_session in sessions:
                user_session.is_active = False

            session.commit()

    def create_new_session(self, user_id: int, **kwargs) -> UserSession:
        """Создать новую сессию (деактивируя старые)"""
        # Деактивируем старые сессии
        self.deactivate_all_sessions(user_id)

        # Создаем новую сессию
        return self.create(user_id=user_id, **kwargs)