# app/database/repositories/content_repo.py
from typing import List, Optional
from app.database.repositories.base import BaseRepository
from app.database.models.content import GeneratedContent


class ContentRepository(BaseRepository[GeneratedContent]):
    def __init__(self):
        super().__init__(GeneratedContent)

    def get_user_content(self, user_id: int) -> List[GeneratedContent]:
        """Получить весь сгенерированный контент пользователя"""
        with self.get_session() as session:
            return (
                session.query(GeneratedContent)
                .filter(GeneratedContent.user_id == user_id)
                .order_by(GeneratedContent.created_at.desc())
                .all()
            )

    def get_session_content(self, session_id: str) -> Optional[GeneratedContent]:
        """Получить контент по ID сессии"""
        with self.get_session() as session:
            return (
                session.query(GeneratedContent)
                .filter(GeneratedContent.session_id == session_id)
                .first()
            )

    def create_content(self, **kwargs) -> GeneratedContent:
        """Создать запись сгенерированного контента"""
        return self.create(**kwargs)