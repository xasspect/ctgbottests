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

    def update_session_data(self, session_id: str, **kwargs):
        """Обновление данных сессии"""
        session = self.get_session()
        try:
            db_session = session.query(UserSession).filter(UserSession.id == session_id).first()
            if db_session:
                for key, value in kwargs.items():
                    setattr(db_session, key, value)
                session.commit()
                session.refresh(db_session)
                logger.info(f"✅ Сессия {session_id} обновлена: {kwargs}")
                return db_session
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка обновления сессии: {e}")
            raise
        finally:
            session.close()

    def get_by_id(self, session_id: str) -> Optional[UserSession]:
        """Получить сессию по ID"""
        with self.get_session() as session:
            return session.query(UserSession).filter(UserSession.id == session_id).first()

    def deactivate_all_sessions(self, user_id: int):
        """Деактивировать все активные сессии пользователя"""
        with self.get_session() as session:
            try:
                # Находим все активные сессии пользователя
                active_sessions = session.query(UserSession).filter(
                    UserSession.user_id == str(user_id),
                    UserSession.is_active == True
                ).all()

                for user_session in active_sessions:
                    user_session.is_active = False

                session.commit()
                logger.info(f"✅ Деактивировано {len(active_sessions)} активных сессий пользователя {user_id}")
                return len(active_sessions)
            except Exception as e:
                session.rollback()
                logger.error(f"❌ Ошибка деактивации сессий: {e}")
                raise

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

    def cleanup_old_sessions(self, user_id: int, keep_count: int = 5):
        """Очистка старых сессий, оставляя только keep_count последних"""
        with self.get_session() as session:
            try:
                # Получаем все сессии пользователя, отсортированные по дате создания
                all_sessions = (
                    session.query(UserSession)
                    .filter(UserSession.user_id == user_id)
                    .order_by(UserSession.created_at.desc())
                    .all()
                )

                # Если сессий больше, чем нужно оставить, удаляем старые
                if len(all_sessions) > keep_count:
                    sessions_to_delete = all_sessions[keep_count:]
                    for old_session in sessions_to_delete:
                        session.delete(old_session)

                    session.commit()
                    logger.info(f"✅ Удалено {len(sessions_to_delete)} старых сессий пользователя {user_id}")

            except Exception as e:
                logger.error(f"❌ Ошибка очистки старых сессий: {e}")
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
