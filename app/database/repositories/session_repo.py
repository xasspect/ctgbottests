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
                    UserSession.user_id == user_id,
                    UserSession.is_active == True
                )
                .first()
            )

            # Специальное логирование для отладки
            if result:
                logger.info(
                    f"✅ Найдена активная сессия: ID={result.id}, Шаг={result.current_step}, Категория={result.category_id}, Назначение={result.purpose}")
            else:
                logger.info(f"❌ Активная сессия не найдена для пользователя {user_id}")

            return result

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
        session = self.get_session()
        try:
            sessions = session.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).all()

            for user_session in sessions:
                user_session.is_active = False

            session.commit()
            logger.info(f"✅ Деактивировано {len(sessions)} сессий для пользователя {user_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка деактивации сессий: {e}")
            raise
        finally:
            session.close()

    def create_new_session(self, user_id: int, **kwargs) -> UserSession:
        """Создать новую сессию (деактивируя старые)"""
        session = self.get_session()
        try:
            # Деактивируем старые сессии
            old_sessions = session.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            ).all()

            for old_session in old_sessions:
                old_session.is_active = False

            # Создаем новую сессию
            new_session = UserSession(
                user_id=user_id,
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

    def update_session_step(self, session_id: str, step: str, **kwargs) -> Optional[UserSession]:
        """Обновить шаг сессии"""
        session = self.get_session()
        try:
            instance = session.get(UserSession, session_id)
            if instance:
                instance.current_step = step
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
                logger.info(f"✅ Сессия обновлена: ID={session_id}, Шаг={step}")
            return instance
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка обновления сессии {session_id}: {e}")
            raise
        finally:
            session.close()

    # Переопределяем метод update для правильной работы
    def update(self, id: str, **kwargs) -> Optional[UserSession]:
        """Обновить запись с логированием"""
        logger.info(f"🔄 Обновление сессии {id}: {kwargs}")
        session = self.get_session()
        try:
            instance = session.get(UserSession, id)
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
                logger.info(f"✅ Сессия {id} успешно обновлена")
            return instance
        except Exception as e:
            session.rollback()
            logger.error(f"❌ Ошибка обновления сессии {id}: {e}")
            raise
        finally:
            session.close()