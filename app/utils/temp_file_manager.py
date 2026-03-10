# app/utils/temp_file_manager.py
import os
import logging
import atexit
import shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class TempFileManager:
    """Менеджер для автоматического удаления временных файлов"""

    _instance = None
    _files_to_delete = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            # Регистрируем очистку при завершении программы
            atexit.register(cls._instance.cleanup_all)
        return cls._instance

    def mark_for_deletion(self, file_path: str) -> None:
        """Помечает файл для удаления"""
        if file_path and os.path.exists(file_path):
            self._files_to_delete.add(file_path)
            logger.debug(f"📌 Файл помечен для удаления: {file_path}")

    def delete_file(self, file_path: str) -> bool:
        """Немедленно удаляет файл"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                self._files_to_delete.discard(file_path)
                logger.info(f"✅ Файл удален: {file_path}")
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления файла {file_path}: {e}")
        return False

    def cleanup_all(self) -> None:
        """Удаляет все помеченные файлы"""
        deleted_count = 0
        for file_path in list(self._files_to_delete):
            if self.delete_file(file_path):
                deleted_count += 1
        if deleted_count > 0:
            logger.info(f"🧹 Очищено {deleted_count} временных файлов")

    def get_temp_path(self, base_name: str, suffix: str = ".json") -> str:
        """Создает временный путь и помечает его для удаления"""
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_file.close()
        self.mark_for_deletion(temp_file.name)
        return temp_file.name


# Глобальный экземпляр
temp_manager = TempFileManager()