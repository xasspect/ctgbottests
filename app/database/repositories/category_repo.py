from typing import List, Optional
from app.database.repositories.base import BaseRepository
from app.database.models.category import Category


class CategoryRepository(BaseRepository[Category]):
    def __init__(self):
        super().__init__(Category)

    def get_by_name(self, name: str) -> Optional[Category]:
        """Получить категорию по имени"""
        with self.get_session() as session:
            return session.query(Category).filter(Category.name == name).first()

    def get_active_categories(self) -> List[Category]:
        """Получить все активные категории"""
        with self.get_session() as session:
            return session.query(Category).filter(Category.is_active == True).all()

    def get_categories_for_user(self) -> List[Category]:
        """Получить категории для показа пользователю (только активные)"""
        with self.get_session() as session:
            return (
                session.query(Category)
                .filter(Category.is_active == True)
                .order_by(Category.name)
                .all()
            )