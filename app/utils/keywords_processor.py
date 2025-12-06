import os
import json
import pandas as pd
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ExcelToJsonConverter:
    """
    Конвертер Excel файлов в JSON формат
    """

    def __init__(self, preserve_excel: bool = False, target_column: str = "Кластер WB"):
        """
        Инициализация конвертера

        Args:
            preserve_excel: Сохранять ли исходный Excel файл после конвертации
            target_column: Название столбца для извлечения данных (по умолчанию "Кластер WB")
        """
        self.logger = logger
        self.preserve_excel = preserve_excel
        self.target_column = target_column
        self.logger.info(
            f"Инициализирован конвертер ExcelToJsonConverter (preserve_excel={preserve_excel}, target_column={target_column})")

    def extract_words_from_sheet(self, df: pd.DataFrame, sheet_name: str) -> List[str]:
        """
        Извлекает уникальные слова из целевого столбца

        Args:
            df: DataFrame с данными
            sheet_name: Имя листа

        Returns:
            Список уникальных слов
        """
        words = []

        try:
            # Проверяем наличие целевого столбца
            if self.target_column not in df.columns:
                self.logger.warning(
                    f"Столбец '{self.target_column}' не найден в листе '{sheet_name}'. Доступные столбцы: {list(df.columns)}")
                return words

            # Извлекаем значения из столбца
            column_values = df[self.target_column].dropna().astype(str).str.strip()

            # Удаляем дубликаты и пустые строки
            unique_words = list(set([word for word in column_values if word]))

            self.logger.info(f"Из листа '{sheet_name}' извлечено {len(unique_words)} уникальных слов")

            return unique_words

        except Exception as e:
            self.logger.error(f"Ошибка при извлечении слов из листа '{sheet_name}': {str(e)}")
            return words

    def convert_file(self, excel_path: str, json_path: Optional[str] = None) -> str:
        """
        Конвертирует Excel файл в JSON, извлекая только значения из целевого столбца

        Args:
            excel_path: Путь к исходному Excel файлу
            json_path: Путь для сохранения JSON файла

        Returns:
            Путь к созданному JSON файлу

        Raises:
            FileNotFoundError: Если исходный файл не найден
            ValueError: Если произошла ошибка конвертации
        """
        self.logger.info(f"Начало конвертации файла: {excel_path}")
        self.logger.info(f"Целевой столбец для извлечения: '{self.target_column}'")

        try:
            # Проверка существования файла
            if not os.path.exists(excel_path):
                error_msg = f"Файл не найден: {excel_path}"
                self.logger.error(error_msg)
                raise FileNotFoundError(error_msg)

            self.logger.debug(f"Файл существует, размер: {os.path.getsize(excel_path)} байт")

            # Загрузка Excel файла
            self.logger.info(f"Загрузка Excel файла: {excel_path}")

            try:
                excel_data = pd.read_excel(excel_path, sheet_name=None)
                sheet_names = list(excel_data.keys())
                self.logger.info(f"Файл загружен. Листы: {sheet_names}")
                self.logger.debug(f"Количество листов: {len(sheet_names)}")

            except Exception as e:
                error_msg = f"Ошибка загрузки Excel файла: {str(e)}"
                self.logger.error(error_msg)
                self.logger.exception("Подробности ошибки:")
                raise ValueError(error_msg) from e

            # Извлечение слов из всех листов
            self.logger.info(f"Извлечение слов из столбца '{self.target_column}'...")
            all_words = []

            for sheet_name, df in excel_data.items():
                self.logger.debug(f"Обработка листа: {sheet_name}")
                self.logger.debug(f"Размер листа {sheet_name}: {df.shape[0]} строк, {df.shape[1]} столбцов")

                sheet_words = self.extract_words_from_sheet(df, sheet_name)
                all_words.extend(sheet_words)

            # Удаляем дубликаты на уровне всего файла
            unique_words = list(set(all_words))
            self.logger.info(f"Всего извлечено {len(all_words)} слов, уникальных: {len(unique_words)}")

            # Сортировка для удобства (опционально)
            unique_words.sort()

            # Подготовка JSON данных
            json_data = {
                "words": unique_words,
            }

            # Определение пути для JSON файла
            if json_path is None:
                base_path = Path(excel_path).stem
                json_path = f"{base_path}.json"
                self.logger.debug(f"Путь JSON не указан, сгенерирован: {json_path}")

            # Сохранение JSON файла
            self.logger.info(f"Сохранение JSON в файл: {json_path}")

            try:
                with open(json_path, 'w', encoding='utf-8') as json_file:
                    json.dump(json_data, json_file, ensure_ascii=False, indent=2)

                file_size = os.path.getsize(json_path)
                self.logger.info(f"JSON файл сохранен. Размер: {file_size} байт")
                self.logger.debug(f"JSON сохранен по пути: {json_path}")

            except Exception as e:
                error_msg = f"Ошибка сохранения JSON файла: {str(e)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg) from e

            # Удаление исходного Excel файла (если не сохранен)
            if not self.preserve_excel:
                self.logger.info(f"Удаление исходного Excel файла: {excel_path}")

                try:
                    os.remove(excel_path)
                    self.logger.info("Исходный файл успешно удален")
                except PermissionError as e:
                    self.logger.warning(f"Нет прав для удаления файла: {str(e)}")
                except Exception as e:
                    self.logger.error(f"Ошибка при удалении файла: {str(e)}")
                    # Не прерываем выполнение, так как конвертация уже выполнена
            else:
                self.logger.info("Исходный Excel файл сохранен (preserve_excel=True)")

            self.logger.info(
                f"Конвертация завершена успешно. "
                f"Уникальных слов извлечено: {len(unique_words)}, "
                f"JSON файл: {json_path}"
            )

            return json_path

        except Exception as e:
            self.logger.exception(f"Критическая ошибка при конвертации файла {excel_path}")
            raise

    def convert_directory(self, directory_path: str, output_dir: Optional[str] = None,
                          pattern: str = "*.xlsx", recursive: bool = False) -> Dict[str, str]:
        """
        Конвертирует все Excel файлы в директории

        Args:
            directory_path: Путь к директории с Excel файлами
            output_dir: Директория для сохранения JSON файлов
            pattern: Шаблон поиска файлов (по умолчанию *.xlsx)
            recursive: Рекурсивный поиск во вложенных директориях

        Returns:
            Словарь {исходный_файл: созданный_json_файл}
        """
        self.logger.info(f"Конвертация Excel файлов в директории: {directory_path}")
        self.logger.debug(f"Параметры: pattern={pattern}, recursive={recursive}, output_dir={output_dir}")

        if not os.path.exists(directory_path):
            error_msg = f"Директория не найдена: {directory_path}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if output_dir and not os.path.exists(output_dir):
            self.logger.info(f"Создание выходной директории: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

        results = {}

        # Поиск файлов
        import glob
        search_pattern = os.path.join(directory_path, pattern)

        if recursive:
            search_pattern = os.path.join(directory_path, "**", pattern)

        excel_files = glob.glob(search_pattern, recursive=recursive)

        self.logger.info(f"Найдено Excel файлов: {len(excel_files)}")

        if not excel_files:
            self.logger.warning("Excel файлы не найдены")
            return results

        # Конвертация каждого файла
        for i, excel_file in enumerate(excel_files, 1):
            self.logger.info(f"Конвертация файла {i}/{len(excel_files)}: {excel_file}")

            try:
                # Определение пути для JSON файла
                if output_dir:
                    base_name = Path(excel_file).stem
                    json_file = os.path.join(output_dir, f"{base_name}.json")
                else:
                    json_file = None

                # Конвертация
                json_path = self.convert_file(excel_file, json_file)
                results[excel_file] = json_path

            except Exception as e:
                self.logger.error(f"Ошибка при конвертации файла {excel_file}: {str(e)}")
                continue

        self.logger.info(f"Конвертация директории завершена. Успешно: {len(results)}/{len(excel_files)} файлов")
        return results


# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Создание конвертера
    converter = ExcelToJsonConverter(preserve_excel=False, target_column="Кластер WB")

    # Конвертация одного файла
    try:
        results = converter.convert_directory(directory_path='downloads/mpstats', output_dir="keywords")
        print(f"Конвертировано файлов: {len(results)}")
    except Exception as e:
        print(f"Ошибка конвертации директории: {e}")