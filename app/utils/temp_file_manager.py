# app/utils/temp_file_manager.py
import os
import atexit
from pathlib import Path
from typing import Optional
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class TempFileManager:
    """Менеджер для автоматического удаления временных файлов"""

    _instance = None
    _files_to_delete = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            atexit.register(cls._instance.cleanup_all)
        return cls._instance

    def mark_for_deletion(self, file_path: str) -> None:
        """Помечает файл для удаления"""
        if file_path and os.path.exists(file_path):
            self._files_to_delete.add(file_path)
            log.debug(f"File marked for deletion: {file_path}")

    def delete_file(self, file_path: str) -> bool:
        """Немедленно удаляет файл"""
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                self._files_to_delete.discard(file_path)
                log.info(LogCodes.DATA_JSON_DELETE, filename=os.path.basename(file_path))
                return True
        except Exception as e:
            log.warning(LogCodes.SCR_ERROR, error=f"Delete file {file_path}: {e}")
        return False

    def cleanup_all(self) -> None:
        """Удаляет все помеченные файлы"""
        deleted_count = 0
        for file_path in list(self._files_to_delete):
            if self.delete_file(file_path):
                deleted_count += 1
        if deleted_count > 0:
            log.info(LogCodes.DATA_JSON_DELETE, filename=f"{deleted_count} temp files")

    def get_temp_path(self, base_name: str, suffix: str = ".json") -> str:
        """Создает временный путь и помечает его для удаления"""
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_file.close()
        self.mark_for_deletion(temp_file.name)
        return temp_file.name


# Глобальный экземпляр
temp_manager = TempFileManager()