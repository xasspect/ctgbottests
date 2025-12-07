import os
import json
import pandas as pd
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class KeywordsProcessor:
    """
    Процессор для работы с ключевыми словами
    """

    def __init__(self, preserve_excel: bool = False, target_column: str = "Кластер WB"):
        """
        Инициализация процессора

        Args:
            preserve_excel: Сохранять ли исходный Excel файл после конвертации
            target_column: Название столбца для извлечения данных (по умолчанию "Кластер WB")
        """
        self.logger = logger
        self.preserve_excel = preserve_excel
        self.target_column = target_column

        # Путь для сохранения keywords JSON файлов
        self.keywords_dir = os.path.join(
            os.path.dirname(__file__),  # app/utils
            'keywords'
        )
        os.makedirs(self.keywords_dir, exist_ok=True)

        self.logger.info(
            f"Инициализирован процессор KeywordsProcessor (preserve_excel={preserve_excel}, target_column={target_column}, keywords_dir={self.keywords_dir})")

    def extract_keywords_from_sheet(self, df: pd.DataFrame, sheet_name: str) -> List[str]:
        """
        Извлекает уникальные ключевые слова из целевого столбца

        Args:
            df: DataFrame с данными
            sheet_name: Имя листа

        Returns:
            Список уникальных ключевых слов
        """
        keywords = []

        try:
            # Проверяем наличие целевого столбца
            if self.target_column not in df.columns:
                self.logger.warning(
                    f"Столбец '{self.target_column}' не найден в листе '{sheet_name}'. Доступные столбцы: {list(df.columns)}")
                return keywords


            # Извлекаем значения из столбца
            column_values = df[self.target_column].dropna().astype(str).str.strip()

            # Удаляем дубликаты и пустые строки
            unique_keywords = list(set([word for word in column_values if word]))

            self.logger.info(f"Из листа '{sheet_name}' извлечено {len(unique_keywords)} уникальных ключевых слов")

            return unique_keywords

        except Exception as e:
            self.logger.error(f"Ошибка при извлечении ключевых слов из листа '{sheet_name}': {str(e)}")
            return keywords

    def convert_xlsx_to_json(self, excel_path: str, json_path: Optional[str] = None) -> str:
        """
        Конвертирует Excel файл в JSON с ключевыми словами

        Args:
            excel_path: Путь к исходному Excel файлу
            json_path: Путь для сохранения JSON файла

        Returns:
            Путь к созданному JSON файлу
        """
        self.logger.info(f"Конвертация файла: {excel_path}")
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
            if json_path is None:
                base_name = Path(excel_path).stem
                # Сохраняем в папке keywords, а не в той же папке
                json_path = os.path.join(self.keywords_dir, f"{base_name}.json")
                self.logger.debug(f"Путь JSON не указан, сгенерирован: {json_path}")
            self.logger.info(f"Сохранение JSON в файл: {json_path}")


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

            # Извлечение ключевых слов из всех листов
            self.logger.info(f"Извлечение ключевых слов из столбца '{self.target_column}'...")
            all_keywords = []

            for sheet_name, df in excel_data.items():
                self.logger.debug(f"Обработка листа: {sheet_name}")
                self.logger.debug(f"Размер листа {sheet_name}: {df.shape[0]} строк, {df.shape[1]} столбцов")

                sheet_keywords = self.extract_keywords_from_sheet(df, sheet_name)
                all_keywords.extend(sheet_keywords)

            # Удаляем дубликаты на уровне всего файла
            unique_keywords = list(set(all_keywords))
            self.logger.info(f"Всего извлечено {len(all_keywords)} ключевых слов, уникальных: {len(unique_keywords)}")

            # Сортировка для удобства (опционально)
            unique_keywords.sort()

            # Подготовка JSON данных (базовый формат)
            json_data = {
                "keywords": unique_keywords,
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
                f"Уникальных ключевых слов извлечено: {len(unique_keywords)}, "
                f"JSON файл: {json_path}"
            )

            return json_path

        except Exception as e:
            self.logger.exception(f"Критическая ошибка при конвертации файла {excel_path}")
            raise

    def create_enriched_json(self, excel_path: str, category: str, purpose: str,
                             additional_params: List[str], json_path: Optional[str] = None) -> str:
        """
        Создает обогащенный JSON файл с 4 колонками:
        - category
        - purpose 
        - additional_params
        - keywords

        Args:
            excel_path: Путь к исходному Excel файлу
            category: Категория товара
            purpose: Назначение товара
            additional_params: Дополнительные параметры
            json_path: Путь для сохранения JSON файла

        Returns:
            Путь к созданному JSON файлу
        """
        try:
            self.logger.info(f"Создание обогащенного JSON из файла: {excel_path}")
            self.logger.info(
                f"Параметры: category={category}, purpose={purpose}, additional_params={additional_params}")

            # Сначала конвертируем Excel в базовый JSON
            base_json_path = self.convert_xlsx_to_json(excel_path)

            if not base_json_path:
                raise ValueError("Не удалось создать базовый JSON файл")

            # Загружаем базовый JSON
            with open(base_json_path, 'r', encoding='utf-8') as f:
                base_data = json.load(f)

            # Получаем ключевые слова
            keywords = base_data.get('words', [])

            # Создаем обогащенную структуру
            enriched_data = {
                'category': category,
                'purpose': purpose,
                'additional_params': additional_params,
                'keywords': keywords
            }

            # Определение пути для обогащенного JSON файла
            if json_path is None:
                base_name = Path(excel_path).stem
                safe_category = category.replace('/', '_').replace(' ', '_')
                # Сохраняем в папке keywords
                json_path = os.path.join(self.keywords_dir, f"{safe_category}_enriched.json")
                self.logger.debug(f"Путь JSON не указан, сгенерирован: {json_path}")

            # Сохранение обогащенного JSON файла
            self.logger.info(f"Сохранение обогащенного JSON в файл: {json_path}")

            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(enriched_data, json_file, ensure_ascii=False, indent=2)

            file_size = os.path.getsize(json_path)
            self.logger.info(f"Обогащенный JSON файл сохранен. Размер: {file_size} байт")

            # Удаляем базовый JSON файл
            try:
                if os.path.exists(base_json_path) and base_json_path != json_path:
                    os.remove(base_json_path)
                    self.logger.info(f"Базовый JSON файл удален: {base_json_path}")
            except Exception as e:
                self.logger.warning(f"Не удалось удалить базовый JSON файл: {str(e)}")

            self.logger.info(
                f"Обогащенный JSON создан успешно. "
                f"Ключевых слов: {len(keywords)}, "
                f"Файл: {json_path}"
            )

            return json_path

        except Exception as e:
            self.logger.exception(f"Критическая ошибка при создании обогащенного JSON из файла {excel_path}")
            raise

    def load_keywords_from_json(self, json_file_path: str) -> List[str]:
        """
        Загружает ключевые слова из JSON файла

        Args:
            json_file_path: Путь к JSON файлу

        Returns:
            Список ключевых слов
        """
        try:
            if not os.path.exists(json_file_path):
                self.logger.error(f"JSON файл не найден: {json_file_path}")
                return []

            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Пытаемся получить ключевые слова из разных форматов
            if 'keywords' in data:
                return data['keywords']
            elif 'words' in data:
                return data['words']
            else:
                self.logger.warning(f"Ключевые слова не найдены в JSON: {json_file_path}")
                return []

        except Exception as e:
            self.logger.error(f"Ошибка загрузки ключевых слов: {str(e)}")
            return []


# Пример использования
if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Создание процессора
    processor = KeywordsProcessor(preserve_excel=False, target_column="Кластер WB")

    # Пример конвертации одного файла
    try:
        # Укажите путь к тестовому XLSX файлу
        test_xlsx = "downloads/mpstats/test.xlsx"
        if os.path.exists(test_xlsx):
            enriched_json = processor.create_enriched_json(
                excel_path=test_xlsx,
                category="electronics",
                purpose="продажа",
                additional_params=["новинка", "скидка"]
            )
            print(f"Обогащенный JSON создан: {enriched_json}")

            # Загрузка ключевых слов для проверки
            keywords = processor.load_keywords_from_json(enriched_json)
            print(f"Загружено ключевых слов: {len(keywords)}")
            print(f"Примеры: {keywords[:5]}")
        else:
            print(f"Тестовый файл не найден: {test_xlsx}")
    except Exception as e:
        print(f"Ошибка: {e}")