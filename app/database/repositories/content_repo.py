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

    def save_generation_result(self, session_id: str, user_id: int,
                               title: str, short_desc: str, long_desc: str,
                               ozon_title: str, ozon_desc: str,
                               keywords: list, category_id: str, purposes: list) -> Optional[GeneratedContent]:
        """
        Сохраняет полный результат генерации для сессии.
        """
        session = self.get_session()
        try:
            # Проверяем, есть ли уже запись для этой сессии
            existing = session.query(GeneratedContent).filter(
                GeneratedContent.session_id == session_id
            ).first()

            if existing:
                # Обновляем существующую
                existing.title = title or existing.title
                existing.short_description = short_desc or existing.short_description
                existing.long_description = long_desc or existing.long_description
                existing.ozon_title = ozon_title or existing.ozon_title
                existing.ozon_description = ozon_desc or existing.ozon_description
                existing.keywords = keywords or existing.keywords
                existing.category_id = category_id or existing.category_id
                existing.purpose = ", ".join(purposes) if purposes else existing.purpose

                session.commit()
                session.refresh(existing)
                self.logger.info(f"✅ Обновлена запись контента для сессии {session_id}")
                return existing
            else:
                # Создаем новую
                new_content = GeneratedContent(
                    session_id=session_id,
                    user_id=user_id,
                    title=title,
                    short_description=short_desc,
                    long_description=long_desc,
                    ozon_title=ozon_title,
                    ozon_description=ozon_desc,
                    keywords=keywords,
                    category_id=category_id,
                    purpose=", ".join(purposes) if purposes else None
                )
                session.add(new_content)
                session.commit()
                session.refresh(new_content)
                self.logger.info(f"✅ Создана новая запись контента для сессии {session_id}")
                return new_content

        except Exception as e:
            session.rollback()
            self.logger.error(f"❌ Ошибка сохранения результата генерации: {e}")
            return None
        finally:
            session.close()

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