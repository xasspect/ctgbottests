# app/utils/keywords_processor.py
import os
import json
import pandas as pd
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging
import re
from app.utils.temp_file_manager import temp_manager
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class KeywordsProcessor:
    """Процессор для работы с ключевыми словами"""

    def __init__(self, preserve_excel: bool = False, target_column: str = "Кластер WB",
                 auto_delete_json: bool = True):
        self.preserve_excel = preserve_excel
        self.target_column = target_column
        self.auto_delete_json = auto_delete_json

        self.keywords_dir = os.path.join(
            os.path.dirname(__file__),
            'keywords'
        )
        os.makedirs(self.keywords_dir, exist_ok=True)

    def extract_keywords_from_sheet(self, df: pd.DataFrame, sheet_name: str) -> List[str]:
        """Извлекает уникальные ключевые слова из первого столбца таблицы"""
        keywords = []

        try:
            first_column_name = df.columns[0]
            column_values = df.iloc[:, 0].dropna().astype(str).str.strip()

            filtered_keywords = []

            for word in column_values:
                word_str = str(word).strip()

                if word_str.isdigit():
                    continue

                if re.match(r'^\d+[штх\.,]?\d*$', word_str):
                    continue

                letters_only = re.sub(r'[^а-яА-Яa-zA-Z]', '', word_str)
                if len(letters_only) < 2:
                    continue

                if not any(c.isalpha() for c in word_str):
                    continue

                if not re.search(r'[а-яА-Я]', word_str):
                    continue

                filtered_keywords.append(word_str)

                if len(filtered_keywords) >= 100:
                    break

            unique_keywords = list(set(filtered_keywords))
            unique_keywords.sort()

            return unique_keywords[:100]

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Extract keywords: {e}")
            return keywords

    def convert_xlsx_to_json(self, excel_path: str, json_path: Optional[str] = None,
                             auto_delete: bool = False) -> str:
        """Конвертирует Excel файл в JSON с ключевыми словами"""
        try:
            if not os.path.exists(excel_path):
                raise FileNotFoundError(f"Файл не найден: {excel_path}")

            excel_data = pd.read_excel(excel_path, sheet_name=None)
            sheet_names = list(excel_data.keys())

            all_keywords = []

            for sheet_name, df in excel_data.items():
                sheet_keywords = self.extract_keywords_from_sheet(df, sheet_name)
                all_keywords.extend(sheet_keywords)

            unique_keywords = list(set(all_keywords))
            unique_keywords.sort()

            max_keywords = 200
            if len(unique_keywords) > max_keywords:
                unique_keywords = unique_keywords[:max_keywords]

            json_data = {
                "keywords": unique_keywords,
                "total_keywords": len(unique_keywords),
                "source_file": os.path.basename(excel_path),
                "extraction_method": "first_column_filtered"
            }

            if json_path is None:
                base_name = Path(excel_path).stem
                json_path = os.path.join(self.keywords_dir, f"{base_name}_filtered.json")

            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(json_data, json_file, ensure_ascii=False, indent=2)

            if auto_delete:
                temp_manager.mark_for_deletion(json_path)

            log.info(LogCodes.DATA_JSON_SAVE, filename=os.path.basename(json_path))
            return json_path

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Convert XLSX to JSON: {e}")
            raise

    def create_enriched_json(self, excel_path: str, category: str, purpose: Union[str, List[str]],
                             additional_params: List[str], json_path: Optional[str] = None,
                             auto_delete: bool = True) -> str:
        """Создает обогащенный JSON файл"""
        try:
            base_json_path = self.convert_xlsx_to_json(excel_path, auto_delete=True)

            if not base_json_path:
                raise ValueError("Не удалось создать базовый JSON файл")

            with open(base_json_path, 'r', encoding='utf-8') as f:
                base_data = json.load(f)

            keywords = base_data.get('keywords', [])

            enriched_data = {
                'category': category,
                'purpose': purpose,
                'additional_params': additional_params,
                'keywords': keywords,
                'purposes': purpose if isinstance(purpose, list) else [purpose] if purpose else []
            }

            if json_path is None:
                safe_category = category.replace('/', '_').replace(' ', '_')
                purpose_str = ""
                if isinstance(purpose, list):
                    purpose_str = '_'.join(purpose[:2]) if purpose else 'all'
                else:
                    purpose_str = str(purpose) if purpose else 'all'
                purpose_str = purpose_str.replace('/', '_').replace(' ', '_').replace('\\', '_')[:20]
                json_path = os.path.join(self.keywords_dir, f"{safe_category}_{purpose_str}_enriched.json")

            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(enriched_data, json_file, ensure_ascii=False, indent=2)

            if auto_delete:
                temp_manager.mark_for_deletion(json_path)

            try:
                if os.path.exists(base_json_path) and base_json_path != json_path:
                    os.remove(base_json_path)
            except Exception:
                pass

            return json_path

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Create enriched JSON: {e}")
            raise

    def load_keywords_from_json(self, json_file_path: str) -> List[str]:
        """Загружает ключевые слова из JSON файла"""
        try:
            if not os.path.exists(json_file_path):
                return []

            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'keywords' in data:
                return data['keywords']
            elif 'words' in data:
                return data['words']
            else:
                return []

        except Exception as e:
            log.error(LogCodes.ERR_MPSTATS, error=f"Load keywords: {e}")
            return []