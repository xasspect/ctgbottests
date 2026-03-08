import os
import json
import pandas as pd
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
import re #ХАХАХАХАХАХХАХАХАХАХАХАХАХАХАХХАХАААХАХХАХАХААХААХААХААХА

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
        Извлекает уникальные ключевые слова из ПЕРВОГО столбца таблицы
        Игнорирует цифры и технические данные
        Возвращает первые 100 ключевых слов
        """
        keywords = []

        try:
            self.logger.info("=" * 60)
            self.logger.info(f"📊 ЛИСТ: '{sheet_name}'")
            self.logger.info(f"📊 Размер: {df.shape[0]} строк, {df.shape[1]} столбцов")
            self.logger.info(f"📊 Все столбцы: {list(df.columns)}")

            # 1. Берем ПЕРВЫЙ столбец (индекс 0) - это столбец "Слова"
            first_column_name = df.columns[0]
            self.logger.info(f"✅ Использую ПЕРВЫЙ столбец: '{first_column_name}'")

            # 2. Извлекаем значения из первого столбца
            column_values = df.iloc[:, 0].dropna().astype(str).str.strip()
            self.logger.info(f"📊 Найдено значений в первом столбце: {len(column_values)}")

            # 3. Показываем примеры для отладки
            if len(column_values) > 0:
                sample_values = column_values.head(15).tolist()
                self.logger.info(f"📊 Примеры из первого столбца (первые 15):")
                for i, val in enumerate(sample_values):
                    self.logger.info(f"  {i + 1}. '{val}'")

            # 4. ФИЛЬТРАЦИЯ: удаляем цифры, технические данные и не-слова
            filtered_keywords = []

            for word in column_values:
                word_str = str(word).strip()

                # ИГНОРИРУЕМ:
                # 1. Чистые цифры (2020, 30, 5055 и т.д.)
                if word_str.isdigit():
                    continue

                # 2. Цифры с суффиксами (20201000, 60шт, 70х77)
                if re.match(r'^\d+[штх\.,]?\d*$', word_str):
                    continue

                # 3. Слишком короткие слова (меньше 2 букв)
                # Сначала удаляем все не-буквы для проверки длины
                letters_only = re.sub(r'[^а-яА-Яa-zA-Z]', '', word_str)
                if len(letters_only) < 2:
                    continue

                # 4. Технические коды (только цифры и символы)
                if not any(c.isalpha() for c in word_str):
                    continue

                # 5. Проверяем, что есть хотя бы одна русская буква
                if not re.search(r'[а-яА-Я]', word_str):
                    continue

                # Если слово прошло все фильтры - добавляем
                filtered_keywords.append(word_str)

                # ОГРАНИЧИВАЕМ до 100 ключевых слов
                if len(filtered_keywords) >= 100:
                    self.logger.info(f"📊 Достигнут лимит в 100 ключевых слов")
                    break

            # 5. Удаляем дубликаты
            unique_keywords = list(set(filtered_keywords))
            unique_keywords.sort()  # Сортируем для удобства

            self.logger.info(f"📊 После фильтрации:")
            self.logger.info(f"  - Исходно: {len(column_values)} значений")
            self.logger.info(f"  - После фильтрации: {len(filtered_keywords)}")
            self.logger.info(f"  - Уникальных: {len(unique_keywords)}")

            # 6. Показываем результат фильтрации
            if unique_keywords:
                self.logger.info(f"📊 Результат фильтрации (первые 20):")
                for i, word in enumerate(unique_keywords[:20]):
                    self.logger.info(f"  {i + 1}. '{word}'")

            self.logger.info("=" * 60)

            return unique_keywords[:100]  # <-- Возвращаем максимум 100 ключевых слов

        except Exception as e:
            self.logger.error(f"❌ Ошибка при извлечении ключевых слов из листа '{sheet_name}': {str(e)}")
            self.logger.exception("Подробности ошибки:")
            return keywords

    def convert_xlsx_to_json(self, excel_path: str, json_path: Optional[str] = None) -> str:
        """
        Конвертирует Excel файл в JSON с ключевыми словами
        ТОЛЬКО из первого столбца, с фильтрацией
        """
        self.logger.info(f"📂 Конвертация файла: {excel_path}")

        try:
            # Проверяем файл
            if not os.path.exists(excel_path):
                raise FileNotFoundError(f"Файл не найден: {excel_path}")

            # Загружаем Excel файл
            excel_data = pd.read_excel(excel_path, sheet_name=None)
            sheet_names = list(excel_data.keys())
            self.logger.info(f"📑 Листы в файле: {sheet_names}")

            all_keywords = []

            for sheet_name, df in excel_data.items():
                self.logger.info(f"📊 Лист '{sheet_name}': {df.shape[0]} строк, {df.shape[1]} столбцов")
                self.logger.info(f"📊 Столбцы: {list(df.columns)}")

                # Показываем первые 3 строки первого столбца для отладки
                if len(df) > 0:
                    self.logger.info(f"📊 Первые 5 строк ПЕРВОГО столбца:")
                    for i in range(min(5, len(df))):
                        first_col_value = str(df.iloc[i, 0]) if pd.notna(df.iloc[i, 0]) else "ПУСТО"
                        self.logger.info(f"  Строка {i}: '{first_col_value}'")

                # Извлекаем ключевые слова из этого листа
                sheet_keywords = self.extract_keywords_from_sheet(df, sheet_name)
                all_keywords.extend(sheet_keywords)

            # Удаляем дубликаты на уровне всего файла
            unique_keywords = list(set(all_keywords))
            self.logger.info(f"📊 ИТОГО по всем листам:")
            self.logger.info(f"  - Собрано: {len(all_keywords)} ключевых слов")
            self.logger.info(f"  - Уникальных: {len(unique_keywords)}")

            # Сортировка для удобства
            unique_keywords.sort()

            # Ограничиваем количество (если нужно)
            max_keywords = 200
            if len(unique_keywords) > max_keywords:
                self.logger.info(f"📊 Ограничиваю до {max_keywords} ключевых слов")
                unique_keywords = unique_keywords[:max_keywords]

            # Показываем окончательный результат
            self.logger.info(f"📊 ФИНАЛЬНЫЙ результат (первые 30):")
            for i, word in enumerate(unique_keywords[:30]):
                self.logger.info(f"  {i + 1}. '{word}'")

            # Подготовка JSON данных
            json_data = {
                "keywords": unique_keywords,
                "total_keywords": len(unique_keywords),
                "source_file": os.path.basename(excel_path),
                "extraction_method": "first_column_filtered",
                "filtered_out": ["чистые цифры", "технические коды", "короткие слова без букв"]
            }

            # Определение пути для JSON файла
            if json_path is None:
                base_name = Path(excel_path).stem
                json_path = os.path.join(self.keywords_dir, f"{base_name}_filtered.json")

            # Сохранение JSON файла
            self.logger.info(f"💾 Сохранение JSON в файл: {json_path}")

            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=2)

            file_size = os.path.getsize(json_path)
            self.logger.info(f"✅ JSON файл сохранен.")
            self.logger.info(f"✅ Конвертация завершена успешно. Уникальных ключевых слов: {len(unique_keywords)}")

            return json_path

        except Exception as e:
            self.logger.exception(f"❌ Критическая ошибка при конвертации файла {excel_path}")
            raise

    def create_enriched_json(self, excel_path: str, category: str, purpose: Union[str, List[str]],
                             additional_params: List[str], json_path: Optional[str] = None) -> str:
        """
        Создает обогащенный JSON файл с 4 колонками
        """
        try:
            self.logger.info(f"Создание обогащенного JSON из файла: {excel_path}")
            self.logger.info(
                f"Параметры: category={category}, purpose={purpose}, additional_params={additional_params}")

            # 1. Сначала конвертируем Excel в базовый JSON
            base_json_path = self.convert_xlsx_to_json(excel_path)

            if not base_json_path:
                raise ValueError("Не удалось создать базовый JSON файл")

            # 2. Загружаем базовый JSON
            with open(base_json_path, 'r', encoding='utf-8') as f:
                base_data = json.load(f)

            # 3. Получаем ключевые слова (исправленная логика)
            keywords = []

            # Пробуем разные ключи
            possible_keys = ['keywords', 'words', 'key_words', 'data']
            for key in possible_keys:
                if key in base_data:
                    keywords = base_data[key]
                    self.logger.info(f"✅ Ключевые слова найдены по ключу '{key}': {len(keywords)} слов")
                    break

            # Если не нашли по ключам, пробуем получить первый список в данных
            if not keywords and base_data:
                # Ищем любой список в данных
                for key, value in base_data.items():
                    if isinstance(value, list):
                        keywords = value
                        self.logger.info(f"✅ Найден список по ключу '{key}': {len(keywords)} элементов")
                        break

            self.logger.info(f"📊 Итоговое количество ключевых слов для сохранения: {len(keywords)}")

            # 4. Создаем обогащенную структуру
            enriched_data = {
                'category': category,
                'purpose': purpose,
                'additional_params': additional_params,
                'keywords': keywords,  # Здесь должны быть ключевые слова
                'purposes': purpose if isinstance(purpose, list) else [purpose] if purpose else []
            }

            # 5. Определение пути для обогащенного JSON файла
            if json_path is None:
                safe_category = category.replace('/', '_').replace(' ', '_')

                # Формируем имя файла из назначения
                purpose_str = ""
                if isinstance(purpose, list):
                    purpose_str = '_'.join(purpose[:2]) if purpose else 'all'
                else:
                    purpose_str = str(purpose) if purpose else 'all'

                # Убираем запрещенные символы
                purpose_str = purpose_str.replace('/', '_').replace(' ', '_').replace('\\', '_')[:20]

                json_path = os.path.join(self.keywords_dir, f"{safe_category}_{purpose_str}_enriched.json")
                self.logger.debug(f"Путь JSON сгенерирован: {json_path}")

            # 6. Сохранение обогащенного JSON файла
            self.logger.info(f"Сохранение обогащенного JSON в файл: {json_path}")
            self.logger.info(f"📊 Сохраняемые данные: keywords={len(keywords)}, category={category}")

            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(enriched_data, json_file, ensure_ascii=False, indent=2)

            file_size = os.path.getsize(json_path)
            self.logger.info(f"Обогащенный JSON файл сохранен. Размер: {file_size} байт")

            # 7. Проверяем сохраненные данные
            with open(json_path, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                saved_keywords_count = len(saved_data.get('keywords', []))
                self.logger.info(f"✅ Проверка: в сохраненном файле {saved_keywords_count} ключевых слов")

            # 8. Удаляем базовый JSON файл (если нужно)
            try:
                if os.path.exists(base_json_path) and base_json_path != json_path:
                    os.remove(base_json_path)
                    self.logger.info(f"Базовый JSON файл удален: {base_json_path}")
            except Exception as e:
                self.logger.warning(f"Не удалось удалить базовый JSON файл: {str(e)}")

            self.logger.info(
                f"✅ Обогащенный JSON создан успешно. "
                f"Ключевых слов: {len(keywords)}, "
                f"Файл: {json_path}"
            )

            return json_path

        except Exception as e:
            self.logger.exception(f"❌ Критическая ошибка при создании обогащенного JSON из файла {excel_path}")
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