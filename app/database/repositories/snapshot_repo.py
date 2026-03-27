# app/database/repositories/snapshot_repo.py
from typing import List, Optional, Dict, Any
import uuid
import json
import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.repositories.base import BaseRepository
from app.database.models.snapshot import ContentSnapshot
import pandas as pd
from pathlib import Path
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class SnapshotRepository(BaseRepository[ContentSnapshot]):
    """Репозиторий для работы со снимками контента"""

    def __init__(self):
        super().__init__(ContentSnapshot)
        self.excel_dir = Path("content_snapshots")
        self.excel_dir.mkdir(exist_ok=True)

    def create_snapshot(self, user_id: int, session_id: str, context: Dict[str, Any],
                        content: Dict[str, Any], generation_type: str, marketplace: str) -> ContentSnapshot:
        """
        Создает снимок генерации контента
        """
        session = self.get_session()
        try:
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

            snapshot = ContentSnapshot(**snapshot_data)
            session.add(snapshot)
            session.commit()
            session.refresh(snapshot)

            log.info(LogCodes.GEN_SNAPSHOT, id=snapshot.id[:8])

            self._append_to_excel(snapshot)

            return snapshot

        except Exception as e:
            session.rollback()
            log.error(LogCodes.ERR_DATABASE, error=f"Create snapshot: {e}")
            raise
        finally:
            session.close()

    def _append_to_excel(self, snapshot: ContentSnapshot):
        """Добавляет снимок в Excel файл"""
        try:
            today = datetime.now()
            filename = self.excel_dir / f"snapshots_{today.strftime('%Y_%m')}.xlsx"

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

            if filename.exists():
                df = pd.read_excel(filename)
                new_row = pd.DataFrame([row_data])
                df = pd.concat([df, new_row], ignore_index=True)
            else:
                df = pd.DataFrame([row_data])

            df.to_excel(filename, index=False)

        except Exception as e:
            log.warning(LogCodes.ERR_DATABASE, error=f"Excel append: {e}")

    def get_user_snapshots(self, user_id: int, limit: int = 50) -> List[ContentSnapshot]:
        """Получает последние снимки пользователя"""
        with self.get_session() as session:
            snapshots = session.query(ContentSnapshot) \
                .filter(ContentSnapshot.user_id == user_id) \
                .order_by(ContentSnapshot.created_at.desc()) \
                .limit(limit) \
                .all()
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
                log.info(LogCodes.DATA_EXCEL_LOAD, filename=output_path)
                return str(output_path)
            return None

    def get_recent_snapshots(self, limit: int = 10) -> List[ContentSnapshot]:
        """Получает последние снимки без фильтрации по пользователю"""
        with self.get_session() as session:
            snapshots = session.query(ContentSnapshot) \
                .order_by(ContentSnapshot.created_at.desc()) \
                .limit(limit) \
                .all()
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