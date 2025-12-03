from typing import List, Optional
import uuid
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
                    UserSession.user_id == user_id,  # Теперь integer
                    UserSession.is_active == True
                )
                .first()
            )

    def get_user_sessions(self, user_id: int) -> List[UserSession]:
        """Получить все сессии пользователя"""
        with self.get_session() as session:
            return (
                session.query(UserSession)
                .filter(UserSession.user_id == user_id)  # Теперь integer
                .order_by(UserSession.created_at.desc())
                .all()
            )

    def deactivate_all_sessions(self, user_id: int) -> None:
        """Деактивировать все сессии пользователя"""
        with self.get_session() as session:
            sessions = session.query(UserSession).filter(
                UserSession.user_id == user_id,  # Теперь integer
                UserSession.is_active == True
            ).all()

            for user_session in sessions:
                user_session.is_active = False

            session.commit()

    def create_new_session(self, user_id: int, **kwargs) -> UserSession:
        """Создать новую сессию (деактивируя старые)"""
        # Деактивируем старые сессии
        self.deactivate_all_sessions(user_id)

        # Теперь user_id уже integer
        kwargs['user_id'] = user_id

        # Создаем новую сессию
        return self.create(**kwargs)

    def update_session_step(self, session_id: str, step: str, **kwargs) -> Optional[UserSession]:
        """Обновить шаг сессии"""
        updates = {'current_step': step, **kwargs}
        return self.update(session_id, **updates)