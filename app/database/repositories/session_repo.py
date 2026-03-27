# app/database/repositories/session_repo.py
from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy.orm import Session
from app.database.repositories.base import BaseRepository
from app.database.models.session import UserSession
import logging

from app.utils.log_codes import LogCodes
from app.utils.logger import log

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository[UserSession]):
    def __init__(self):
        super().__init__(UserSession)

    # app/database/repositories/session_repo.py

    def update_session_data(self, session_id: str, **kwargs):
        """Обновление данных сессии"""
        session = self.get_session()
        try:
            db_session = session.query(UserSession).filter(UserSession.id == session_id).first()
            if db_session:
                for key, value in kwargs.items():
                    if hasattr(db_session, key):
                        if isinstance(value, list):
                            setattr(db_session, key, value)
                        else:
                            setattr(db_session, key, value)

                session.commit()
                session.refresh(db_session)
                return db_session
            return None
        except Exception as e:
            session.rollback()
            log.error(LogCodes.ERR_DATABASE, error=str(e))
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
                active_sessions = session.query(UserSession).filter(
                    UserSession.user_id == str(user_id),
                    UserSession.is_active == True
                ).all()

                for user_session in active_sessions:
                    user_session.is_active = False

                session.commit()
                return len(active_sessions)
            except Exception as e:
                session.rollback()
                log.error(LogCodes.ERR_DATABASE, error=str(e))
                raise

    def get_active_session(self, user_id: int) -> Optional[UserSession]:
        """Получить активную сессию пользователя"""
        with self.get_session() as session:
            try:
                result = (
                    session.query(UserSession)
                    .filter(
                        UserSession.user_id == str(user_id),
                        UserSession.is_active == True
                    )
                    .first()
                )

                if result:
                    log.info(LogCodes.DB_SESSION_ACTIVE, id=result.id[:8])
                return result
            except Exception as e:
                log.error(LogCodes.ERR_DATABASE, error=str(e))
                return None

    def cleanup_old_sessions(self, user_id: int, keep_count: int = 5):
        """Очистка старых сессий, оставляя только keep_count последних"""
        with self.get_session() as session:
            try:
                all_sessions = (
                    session.query(UserSession)
                    .filter(UserSession.user_id == user_id)
                    .order_by(UserSession.created_at.desc())
                    .all()
                )

                if len(all_sessions) > keep_count:
                    sessions_to_delete = all_sessions[keep_count:]
                    for old_session in sessions_to_delete:
                        session.delete(old_session)

                    session.commit()
                    logger.info(f"✅ Удалено {len(sessions_to_delete)} старых сессий пользователя {user_id}")

            except Exception as e:
                logger.error(f"❌ Ошибка очистки старых сессий: {e}")

    def create_new_session(self, user_id: int, **kwargs) -> UserSession:
        """Создать новую сессию"""
        session = self.get_session()
        try:
            from app.database.repositories.user_repo import UserRepository

            user_repo = UserRepository()
            user = user_repo.get_by_telegram_id(user_id)

            if not user:
                user = user_repo.get_or_create(
                    telegram_id=user_id,
                    username=kwargs.get('username'),
                    first_name=kwargs.get('first_name'),
                    last_name=kwargs.get('last_name')
                )

            old_sessions = session.query(UserSession).filter(
                UserSession.user_id == str(user_id),
                UserSession.is_active == True
            ).all()

            for old_session in old_sessions:
                old_session.is_active = False

            session_data = {
                'user_id': str(user_id),
                'is_active': True,
            }

            for key, value in kwargs.items():
                if isinstance(value, list):
                    session_data[key] = value
                else:
                    session_data[key] = value

            new_session = UserSession(**session_data)
            session.add(new_session)
            session.commit()
            session.refresh(new_session)

            log.info(LogCodes.DB_SESSION_CREATED, id=new_session.id[:8])
            return new_session

        except Exception as e:
            session.rollback()
            log.error(LogCodes.ERR_DATABASE, error=str(e))
            raise
        finally:
            session.close()