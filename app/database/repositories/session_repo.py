from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from app.database.repositories.base import BaseRepository
from app.database.models.session import UserSession
import logging

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository[UserSession]):
    def __init__(self):
        super().__init__(UserSession)

    def get_active_session(self, user_id: int) -> Optional[UserSession]:
        """Получить активную сессию пользователя"""
        with self.get_session() as session:
            result = (
                session.query(UserSession)
                .filter(
                    UserSession.user_id == (user_id),  # Преобразуем к строке
                    UserSession.is_active == True
                )
                .first()
            )

            if result:
                logger.info(
                    f"✅ Найдена активная сессия: ID={result.id}, Шаг={result.current_step}, "
                    f"Категория={result.category_id}, Назначение={result.purpose}")
            else:
                logger.info(f"❌ Активная сессия не найдена для пользователя {user_id}")

            return result

    def create_new_session(self, user_id: int, **kwargs) -> UserSession:
        """Создать новую сессию (деактивируя старые)"""
        session = self.get_session()
        try:
            # Деактивируем старые сессии
            old_sessions = session.query(UserSession).filter(
                UserSession.user_id == (user_id),
                UserSession.is_active == True
            ).all()

            for old_session in old_sessions:
                old_session.is_active = False

            # Создаем новую сессию
            new_session = UserSession(
                user_id=str(user_id),  # Преобразуем к строке
                is_active=True,
                **kwargs
            )

            session.add(new_session)
            session.commit()
            session.refresh(new_session)

            logger.info(f"✅ Создана новая сессия: ID={new_session.id}")
            return new_session
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка создания сессии: {e}")
            raise
        finally:
            session.close()
