# app/database/repositories/snapshot_repo.py
from typing import List, Optional, Dict, Any
import uuid
import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.repositories.base import BaseRepository
from app.database.models.snapshot import ContentSnapshot
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)


class SnapshotRepository(BaseRepository[ContentSnapshot]):
    """Репозиторий для работы со снимками контента"""

    def __init__(self):
        super().__init__(ContentSnapshot)
        self.logger = logging.getLogger(__name__)
        # Путь для Excel файлов
        self.excel_dir = Path("content_snapshots")
        self.excel_dir.mkdir(exist_ok=True)

    def create_snapshot(self, user_id: int, session_id: str, context: Dict[str, Any],
                        content: Dict[str, Any], generation_type: str, marketplace: str) -> ContentSnapshot:
        """
        Создает снимок генерации контента

        Args:
            user_id: ID пользователя
            session_id: ID сессии
            context: Словарь с контекстом (category, purposes, additional_params, keywords)
            content: Словарь со сгенерированным контентом
            generation_type: Тип генерации (title, short_desc, long_desc, desc)
            marketplace: Маркетплейс (wb, ozon)
        """
        session = self.get_session()
        try:
            # Подготавливаем данные для снимка
            snapshot_data = {
                'user_id': user_id,
                'session_id': session_id,
                'category_id': context.get('category_id'),
                'category_name': context.get('category_name', ''),
                'purposes': context.get('purposes', []),
                'additional_params': context.get('additional_params', []),
                'keywords': context.get('keywords', []),
                'wb_title': content.get('wb_title'),
                'wb_short_desc': content.get('wb_short_desc'),
                'wb_long_desc': content.get('wb_long_desc'),
                'ozon_title': content.get('ozon_title'),
                'ozon_desc': content.get('ozon_desc'),
                'generation_type': generation_type,
                'marketplace': marketplace,
            }

            # Создаем запись в БД
            snapshot = ContentSnapshot(**snapshot_data)
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)

            self.logger.info(f"✅ Создан снимок {snapshot.id} для пользователя {user_id}")

            # Дублируем в Excel
            self._append_to_excel(snapshot)

            return snapshot

        except Exception as e:
            session.rollback()
            self.logger.error(f"❌ Ошибка создания снимка: {e}")
            raise
        finally:
            session.close()

    def _append_to_excel(self, snapshot: ContentSnapshot):
        """Добавляет снимок в Excel файл"""
        try:
            # Формируем имя файла (новый файл каждый месяц)
            today = datetime.now()
            filename = self.excel_dir / f"snapshots_{today.strftime('%Y_%m')}.xlsx"

            # Подготавливаем данные для строки
            row_data = {
                'timestamp': snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'user_id': snapshot.user_id,
                'session_id': snapshot.session_id,
                'category_id': snapshot.category_id,
                'category_name': snapshot.category_name,
                'purposes': json.dumps(snapshot.purposes, ensure_ascii=False),
                'additional_params': json.dumps(snapshot.additional_params, ensure_ascii=False),
                'keywords_count': len(snapshot.keywords) if snapshot.keywords else 0,
                'keywords': json.dumps(snapshot.keywords, ensure_ascii=False),
                'wb_title': snapshot.wb_title,
                'wb_short_desc': snapshot.wb_short_desc[:100] + '...' if snapshot.wb_short_desc and len(
                    snapshot.wb_short_desc) > 100 else snapshot.wb_short_desc,
                'wb_long_desc_length': len(snapshot.wb_long_desc) if snapshot.wb_long_desc else 0,
                'ozon_title': snapshot.ozon_title,
                'ozon_desc_length': len(snapshot.ozon_desc) if snapshot.ozon_desc else 0,
                'generation_type': snapshot.generation_type,
                'marketplace': snapshot.marketplace,
                'snapshot_id': snapshot.id,
            }

            # Проверяем, существует ли файл
            if filename.exists():
                # Читаем существующий файл
                df = pd.read_excel(filename)
                # Добавляем новую строку
                new_row = pd.DataFrame([row_data])
                df = pd.concat([df, new_row], ignore_index=True)
            else:
                # Создаем новый файл
                df = pd.DataFrame([row_data])

            # Сохраняем
            df.to_excel(filename, index=False)
            self.logger.info(f"✅ Снимок добавлен в Excel: {filename}")

        except Exception as e:
            self.logger.error(f"❌ Ошибка записи в Excel: {e}")

    # app/database/repositories/snapshot_repo.py

    # app/database/repositories/snapshot_repo.py

    def get_user_snapshots(self, user_id: int, limit: int = 50) -> List[ContentSnapshot]:
        """Получает последние снимки пользователя"""
        self.logger.info(f"🔍 Поиск снимков для пользователя {user_id} (тип: {type(user_id)})")

        with self.get_session() as session:
            # Сначала проверим, есть ли вообще снимки в БД
            total_count = session.query(ContentSnapshot).count()
            self.logger.info(f"📊 Всего снимков в БД: {total_count}")

            # Ищем снимки для конкретного пользователя
            snapshots = session.query(ContentSnapshot) \
                .filter(ContentSnapshot.user_id == user_id) \
                .order_by(ContentSnapshot.created_at.desc()) \
                .limit(limit) \
                .all()

            self.logger.info(f"✅ Найдено снимков для пользователя {user_id}: {len(snapshots)}")

            # Если не нашли, проверим все уникальные user_id в БД
            if not snapshots:
                all_users = session.query(ContentSnapshot.user_id).distinct().all()
                self.logger.info(f"👥 Уникальные user_id в БД: {[u[0] for u in all_users]}")

            return snapshots

    def get_snapshots_by_date(self, start_date: datetime, end_date: datetime) -> List[ContentSnapshot]:
        """Получает снимки за период"""
        with self.get_session() as session:
            return session.query(ContentSnapshot) \
                .filter(ContentSnapshot.created_at.between(start_date, end_date)) \
                .order_by(ContentSnapshot.created_at.desc()) \
                .all()

    def export_all_to_excel(self, filepath: Optional[str] = None):
        """Экспортирует все снимки в Excel"""
        with self.get_session() as session:
            snapshots = session.query(ContentSnapshot).order_by(ContentSnapshot.created_at.desc()).all()

            data = []
            for s in snapshots:
                data.append({
                    'timestamp': s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'user_id': s.user_id,
                    'session_id': s.session_id,
                    'category_name': s.category_name,
                    'purposes': json.dumps(s.purposes, ensure_ascii=False),
                    'keywords_count': len(s.keywords) if s.keywords else 0,
                    'wb_title': s.wb_title,
                    'ozon_title': s.ozon_title,
                    'generation_type': s.generation_type,
                    'marketplace': s.marketplace,
                })

            if data:
                df = pd.DataFrame(data)
                output_path = filepath or self.excel_dir / f"all_snapshots_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                df.to_excel(output_path, index=False)
                self.logger.info(f"✅ Экспортировано {len(data)} снимков в {output_path}")
                return str(output_path)
            return None

    # app/database/repositories/snapshot_repo.py (добавьте эти методы)

    def get_recent_snapshots(self, limit: int = 10) -> List[ContentSnapshot]:
        """Получает последние снимки без фильтрации по пользователю"""
        self.logger.info(f"🔍 Получение последних {limit} снимков")

        with self.get_session() as session:
            snapshots = session.query(ContentSnapshot) \
                .order_by(ContentSnapshot.created_at.desc()) \
                .limit(limit) \
                .all()

            self.logger.info(f"✅ Найдено снимков: {len(snapshots)}")
            return snapshots

    def get_all_snapshots(self, limit: int = 1000) -> List[ContentSnapshot]:
        """Получает все снимки с лимитом"""
        with self.get_session() as session:
            return session.query(ContentSnapshot) \
                .order_by(ContentSnapshot.created_at.desc()) \
                .limit(limit) \
                .all()

    def get_total_count(self) -> int:
        """Получить общее количество снимков в БД"""
        with self.get_session() as session:
            return session.query(ContentSnapshot).count()