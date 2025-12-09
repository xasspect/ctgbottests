# app/utils/admin_utils.py
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class AdminUtils:
    """Утилиты для админ-панели"""

    @staticmethod
    def check_admin_access(user_id: int, admin_id: int, user_role: str) -> bool:
        """Проверка доступа администратора"""
        return user_id == admin_id or user_role == 'admin'

    @staticmethod
    def can_promote_admins(user_id: int, admin_id: int) -> bool:
        """Проверка может ли пользователь назначать админов"""
        return user_id == admin_id