# app/services/prompt_service.py

import logging
import re
from typing import Tuple, List, Optional


class PromptService:
    """
    Универсальный сервис генерации SEO-контента
    для Wildberries и Ozon.

    Работает ТОЛЬКО на основе:
    - Заголовок
    - Описание
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    # ============================================================
    # МЕТОД ДЛЯ ФИЛЬТРАЦИИ КЛЮЧЕВЫХ СЛОВ
    # ============================================================

#     def get_keywords_filter_prompt(
#             self,
#             category: str,
#             purposes: List[str],
#             additional_params: List[str],
#             category_description: str = "",
#             max_keywords: int = 13
#     ) -> Tuple[str, str]:
#         """
#         Промпт для фильтрации ключевых слов через GPT
#         Отбирает РОВНО 13 самых релевантных ключей по строгому алгоритму
#
#         Args:
#             category: Категория товара
#             purposes: Назначения товара
#             additional_params: Дополнительные параметры
#             category_description: Описание категории
#             max_keywords: Сколько ключевых слов оставить
#
#         Returns:
#             Кортеж (system_prompt, user_prompt)
#         """
#         purposes_text = ", ".join(purposes) if purposes else "не указаны"
#         params_text = ", ".join(additional_params) if additional_params else "не указаны"
#
#         system_prompt = f"""Ты SEO-аналитик маркетплейсов.
#
# Твоя задача:
# Из списка ключевых слов (примерно 30) выбрать РОВНО 13 самых релевантных.
#
# Работай строго по алгоритму.
#
# ЭТАП 1 — Классифицируй каждый ключ по категориям:
# 1. Тип товара
# 2. Материал
# 3. Основной поисковый запрос
# 4. Назначение
# 5. Зона применения
# 6. Цвет / фактура
# 7. Формат
# 8. Размер
# 9. Количество
# 10. Техническое свойство
# 11. SEO-синоним
# 12. Нерелевантный
#
# ЭТАП 2 — Оцени релевантность по шкале 0–5:
# 5 — основной высокочастотный запрос
# 4 — усиливает основной
# 3 — важная характеристика
# 2 — вспомогательный
# 1 — слабый
# 0 — нерелевантный
#
# ЭТАП 3 — Отбери РОВНО 13 ключей по строгой квоте:
# 1 — основной поисковый запрос
# 1 — тип товара
# 1 — материал
# 2 — назначение
# 1 — зона применения
# 2 — технические свойства
# 1 — формат
# 1 — размер
# 1 — количество
# 2 — SEO-синонимы
#
# Если категории нет — перераспредели в свойства или назначение.
#
# ЭТАП 4 — Удали смысловые дубли.
# Оставляй только наиболее частотную форму.
#
# Выведи ТОЛЬКО итоговый список из 13 ключей в правильном порядке приоритета:
# Основной запрос →
# Тип товара →
# Материал →
# Назначение →
# Зона применения →
# Свойства →
# Формат →
# Размер →
# Количество →
# SEO-синонимы
#
# Без объяснений.
# Без комментариев.
# Только список.
# """
#
#         user_prompt = f"""Контекст товара:
# - Категория: {category}
# - Назначения: {purposes_text}
# - Дополнительные параметры: {params_text}
# - Описание категории: {category_description if category_description else "не указано"}
#
# Список ключевых слов для фильтрации:
# {{keywords_list}}
#
# Отбери из списка РОВНО 13 самых релевантных ключевых слов, строго следуя алгоритму.
#
# Формат ответа: слово1, слово2, слово3, слово4, слово5, слово6, слово7, слово8, слово9, слово10, слово11, слово12, слово13"""
#
#         return system_prompt, user_prompt

    def get_keywords_filter_prompt(
            self,
            category: str,
            purposes: List[str],
            additional_params: List[str],
            category_description: str = "",
            max_keywords: int = 25
    ) -> tuple[str, str]:
        """
        Промпт для фильтрации ключевых слов через GPT

        Returns:
            Кортеж (system_prompt, user_prompt)
        """
        purposes_text = ", ".join(purposes) if isinstance(purposes, list) else str(purposes)
        params_text = ", ".join(additional_params) if additional_params else "не указаны"

        system_prompt = f"""Ты — профессиональный маркетолог-копирайтер для маркетплейсов Wildberries и OZON. 
        Твоя задача — отобрать ТОЛЬКО {max_keywords} самых продающих и релевантных ключевых слов из списка 
        для создания заголовков и описаний товаров."""

        user_prompt = f"""
        Контекст товара:
        - Категория: {category}
        - Назначения: {purposes_text}
        - Доп. параметры: {params_text}
        - Описание категории: {category_description if category_description else "не указано"}

        Критерии отбора ключевых слов (В ПРИОРИТЕТЕ):
        1. **Продающие слова** — которые побуждают к покупке (качество, премиум, выгодно, новинка, хит)
        2. **Конкретика** — точные названия товаров/свойств
        3. **Пользовательский язык** — как ищут реальные покупатели
        4. **Релевантность категории** — точно соответствуют "{category}"
        5. **Учет назначений** — подходят для "{purposes_text}"
        6. **SEO-оптимизация** — популярные поисковые запросы на маркетплейсах
        7. **Коммерческий потенциал** — слова, которые конвертируют в продажи

        ИСКЛЮЧАЙ:
        - Общие слова без конкретики (типа "товар", "изделие")
        - Технические термины, не понятные покупателям
        - Слова с ошибками или опечатками
        - Слишком длинные фразы (больше 3 слов)
        - Устаревшие или непопулярные запросы

        Список ключевых слов для фильтрации: {{keywords_list}}

        Формат ответа: ТОЛЬКО список из {max_keywords} ключевых слов через запятую, без нумерации, без пояснений.
        """

        return system_prompt, user_prompt

    # ============================================================
    # ОСНОВНОЙ МЕТОД ГЕНЕРАЦИИ ВСЕГО КОНТЕНТА
    # ============================================================

    def get_marketplace_content_prompt(
            self,
            title_raw: str,
            description_raw: str,
    ) -> Tuple[str, str]:
        """
        Возвращает system и user prompt для генерации:
        - WB TITLE
        - WB SHORT TITLE
        - WB SHORT DESCRIPTION
        - WB FULL DESCRIPTION
        - OZON TITLE
        - OZON FULL DESCRIPTION
        """

        # ================= SYSTEM PROMPT =================

        system_prompt = """
Ты — профессиональный SEO-специалист по маркетплейсам Wildberries и Ozon.

Ты создаешь:
- SEO-заголовки
- краткие описания
- полные SEO-описания

Работаешь строго по правилам маркетплейсов.

========================
ОБЩИЕ ЗАПРЕТЫ:
========================

Запрещено:
- маркетинговые слова
- эмоции
- восклицательные знаки
- капслок
- слова: лучший, качественный, надежный, стильный, премиум, топ, хит, акция
- переспам ключами
- дублирование фраз подряд
- выдумывать характеристики
- повтор одного слова более 2 раз
- знаки препинания
- Не указывать размеры если они не были переданы явно

Работаешь ТОЛЬКО на основе переданных данных.

========================
ПРАВИЛА ДЛЯ WB TITLE:
========================

СТРОГИЙ ПОРЯДОК КЛЮЧЕЙ:

1. Самый частотный поисковый запрос
2. Материал (ПВХ если это панели и они не звукопоглащающие)
3. Назначение
4. Формат
5. Размер или количество (если есть) иначе SEO-синонимы

ЗАПРЕЩЕНО:
- менять порядок
- начинать с цвета
- начинать с размера
- вставлять характеристики раньше основного ключа
- повторять слова
- Использовать знаки препинания
- Указывать размеры если не были переданы явно

Если порядок нарушен — перепиши заголовок.

Дополнительные требования:
- Если в ключевых словах есть материалы: мрамор, кирпич, камень, дерево, то добавляй приставку "под" перед использованием этих ключевых слов, не нарушая лаконичности названия на русском языке.
- Если в ключевых словах есть: кухня, гостиная, ванная, то добавляй "для" перед использованием этих ключевых слов. примеры: для кухни и гостиной, для ванны.
- Без знаков препинания
- Без спецсимволов
- Только факты

========================
ПРАВИЛА ДЛЯ WB SHORT TITLE:
========================

- От 60 до 80 символов
- Максимально релевантно
- Минимум уточнений
- Без маркетинга
- Без знаков препинания

========================
ПРАВИЛА ДЛЯ WB SHORT DESCRIPTION:
========================

- До 1000 символов
- 20–25 релевантных ключей
- Нейтральный тон
- 1–2 абзаца
- Без навязывания
- Без преувеличений

========================
ПРАВИЛА ДЛЯ WB FULL DESCRIPTION:
========================

- 1500–2200 символов
- 4–5 абзацев
- Около 40 ключевых слов
- Один ключ максимум 2 раза
- Без спама
- Без маркетинга

========================
ПРАВИЛА ДЛЯ OZON TITLE:
========================

СТРОГО 120–160 символов.
Если меньше 120 — ОБЯЗАТЕЛЬНО ДОПОЛНИ описание характеристиками.

Формула ОБЯЗАТЕЛЬНА:

Тип товара + материал + основной поисковый запрос + назначение +
цвет / фактура + формат + важные свойства + размер (если был передан в формате "число"x"число" (например 2000x120)) + количество 

Разрешается расширять название за счёт:
- цвета
- размеров
- толщины
- формата
- количества в упаковке
- сферы применения
- технических характеристик
- альтернативных формулировок типа товара

Запрещено:
- маркетинговые слова
- эмоции
- оценочные формулировки
- повтор одного слова более 2 раз

ПЕРЕД ОТВЕТОМ:
1. Посчитай символы.
2. Если меньше 120 — добавь характеристики из входных данных.
3. Только после этого выведи результат.

ВАЖНО: главный поисковый запрос должен быть в начале названия.

========================
ПРАВИЛА ДЛЯ OZON FULL DESCRIPTION:
========================

- 1500–3000 символов
- Структура:
  1) Вводный абзац с основным ключом
  2) Польза и применение
  3) Маркированный список 4–6 пунктов
  4) Где используется
  5) LSI формулировки
- Основной ключ 2–3 раза
- Дополнительные ключи по 1 разу
- Без спама
- Без маркетинга
- Не дублировать название

========================
ФОРМАТ ОТВЕТА СТРОГО:
========================

=== WB_TITLE ===
текст

=== WB_SHORT_TITLE ===
текст

=== WB_SHORT_DESCRIPTION ===
текст

=== WB_FULL_DESCRIPTION ===
текст

=== OZON_TITLE ===
текст

=== OZON_FULL_DESCRIPTION ===
текст
"""

        # ================= USER PROMPT =================

        user_prompt = f"""
Входные данные товара:

Заголовок: {title_raw}

Описание: {description_raw}

На основе этих данных сгенерируй:

1) Название для WB до 60 символов

ТРЕБОВАНИЯ К WB НАЗВАНИЮ:
- строго 60-80 символов
- СТРОГИЙ ПОРЯДОК КЛЮЧЕЙ:
  1. Самый частотный поисковый запрос
  2. Материал (ПВХ если это панели и они не звукопоглащающие)
  3. Назначение
  4. Формат
  5. Размер или количество
- НЕ начинать с цвета или размера
- НЕ менять порядок ключей
- без знаков препинания
- без маркетинга
- Отсутствие размеров если они не были явно переданы в "Дополнительные параметры"

2) Краткий заголовок WB до 50 символов
3) Краткое описание WB до 1000 символов
4) Полное SEO описание WB около 2000 символов
5) SEO название для Ozon

ТРЕБОВАНИЯ К OZON НАЗВАНИЮ:
- строго 120–160 символов
- минимум 120 символов (обязательно!)
- главный поисковый запрос в начале
- добавить максимум характеристик из входных данных
- можно расширять за счет размеров, цвета, материала, назначения, количества
- никаких маркетинговых слов
- Не указывать размеры если они явно не были переданы в формате "число"x"число"

ВАЖНО: если длина меньше 120 символов — продолжай расширять характеристиками из входных данных, пока не достигнешь минимума.

6) Полное SEO описание Ozon 1500–3000 символов

Строго соблюдай все правила.

Верни результат строго в заданном формате.
"""

        return system_prompt.strip(), user_prompt.strip()

    # ============================================================
    # МЕТОДЫ-ОБЁРТКИ ДЛЯ КОНКРЕТНЫХ ТИПОВ КОНТЕНТА
    # ============================================================

    def _build_title_raw(self, category: str, purposes: List[str], keywords: List[str]) -> str:
        """Формирует заголовок из входных данных для передачи в промпт"""
        purposes_text = ", ".join(purposes) if purposes else ""
        keywords_text = ", ".join(keywords[:15]) if keywords else ""

        # Формируем заголовок вида: "Категория: назначения (ключевые слова)"
        title = category
        if purposes_text:
            title += f", {purposes_text}"
        if keywords_text:
            title += f" — {keywords_text}"

        return title

    def _build_description_raw(self, category: str, purposes: List[str],
                               additional_params: List[str], keywords: List[str]) -> str:
        """Формирует описание из входных данных для передачи в промпт"""
        purposes_text = ", ".join(purposes) if purposes else "не указаны"
        params_text = ", ".join(additional_params) if additional_params else "не указаны"
        keywords_text = ", ".join(keywords[:30]) if keywords else "не указаны"

        # Определяем, есть ли размеры в ключевых словах или параметрах
        has_sizes = any(ind in str(keywords_text + params_text).lower()
                        for ind in ['мм', 'см', 'м', 'размер', '×', 'x'])

        size_note = "\n- размеры присутствуют" if has_sizes else "\n- размеры отсутствуют"

        description = (
            f"Категория товара: {category}\n"
            f"Назначения: {purposes_text}\n"
            f"Дополнительные параметры: {params_text}\n"
            f"Ключевые слова: {keywords_text}\n\n"
            f"Характеристики для расширения названия:{size_note}\n"
            f"- возможные цвета: белый, черный, серый, бежевый (если есть в ключевых словах)\n"
            f"- возможные размеры: стандартные (если явно указаны, если нет то размеры не указывать)\n"
            f"- возможные материалы: ПВХ, пластик, МДФ (если есть в ключевых словах)\n"
            f"- формат: панели, плитка, рулон (определи по категории)"
        )

        return description

    def parse_result(self, result: str, section: str) -> str:
        """Парсит результат, извлекая только указанную секцию"""
        try:
            # Логируем первые 500 символов ответа для отладки
            self.logger.info(f"Сырой ответ от GPT (первые 500 символов):\n{result[:500]}")

            # Ищем секцию с разделителями
            pattern = rf"=== {section} ===\n(.*?)(?=\n===|\Z)"
            match = re.search(pattern, result, re.DOTALL | re.MULTILINE)
            if match:
                extracted = match.group(1).strip()
                self.logger.info(f"✅ Извлечена секция {section}, длина: {len(extracted)}")
                return extracted

            # Если не нашли - логируем это
            self.logger.warning(f"⚠️ Секция {section} не найдена в ответе!")
            return result

        except Exception as e:
            self.logger.error(f"❌ Ошибка парсинга секции {section}: {e}")
            return result

    # Методы для Wildberries
    def get_wb_title_prompt(self, category: str, purposes: List[str],
                            additional_params: List[str], keywords: List[str]) -> Tuple[str, str]:
        """
        Промпт для генерации заголовка Wildberries
        Возвращает system_prompt и user_prompt
        """
        # Формируем заголовок и описание из входных данных
        title_raw = self._build_title_raw(category, purposes, keywords)
        description_raw = self._build_description_raw(category, purposes, additional_params, keywords)

        # Получаем универсальные промпты
        system_prompt, user_prompt = self.get_marketplace_content_prompt(title_raw, description_raw)

        # Добавляем в user_prompt указание, что нужен только WB TITLE с акцентом на порядок
        user_prompt += """

Верни ТОЛЬКО секцию WB_TITLE, без остальных секций.

ПЕРЕД ОТВЕТОМ ПРОВЕРЬ:
1. Строгий порядок: частотный запрос → материал → назначение → формат → размер/количество
2. Не начинается с цвета или размера
3. Порядок не нарушен
4. Длина 60-80 символов
5. Нет знаков препинания

Если порядок нарушен — перепиши.
"""

        return system_prompt, user_prompt

    def get_wb_short_desc_prompt(self, category: str, purposes: List[str],
                                 additional_params: List[str], keywords: List[str]) -> Tuple[str, str]:
        """
        Промпт для генерации краткого описания Wildberries
        """
        title_raw = self._build_title_raw(category, purposes, keywords)
        description_raw = self._build_description_raw(category, purposes, additional_params, keywords)

        system_prompt, user_prompt = self.get_marketplace_content_prompt(title_raw, description_raw)
        user_prompt += "\n\nВерни ТОЛЬКО секцию WB_SHORT_DESCRIPTION, без остальных секций."

        return system_prompt, user_prompt

    def get_wb_long_desc_prompt(self, category: str, purposes: List[str],
                                additional_params: List[str], keywords: List[str]) -> Tuple[str, str]:
        """
        Промпт для генерации полного описания Wildberries
        """
        title_raw = self._build_title_raw(category, purposes, keywords)
        description_raw = self._build_description_raw(category, purposes, additional_params, keywords)

        system_prompt, user_prompt = self.get_marketplace_content_prompt(title_raw, description_raw)
        user_prompt += "\n\nВерни ТОЛЬКО секцию WB_FULL_DESCRIPTION, без остальных секций."

        return system_prompt, user_prompt

    # Методы для Ozon
    def get_ozon_title_prompt(self, category: str, purposes: List[str],
                              additional_params: List[str], keywords: List[str],
                              category_description: str = "") -> Tuple[str, str]:
        """
        Промпт для генерации SEO-названия Ozon
        """
        title_raw = self._build_title_raw(category, purposes, keywords)
        if category_description and category_description not in title_raw:
            title_raw = f"{category_description} / {title_raw}"

        description_raw = self._build_description_raw(category, purposes, additional_params, keywords)

        system_prompt, user_prompt = self.get_marketplace_content_prompt(title_raw, description_raw)
        user_prompt += "\n\nВерни ТОЛЬКО секцию OZON_TITLE, без остальных секций."

        # Добавляем дополнительное напоминание о длине
        user_prompt += "\n\nВАЖНО: ПРОВЕРЬ ДЛИНУ! Название должно быть строго 120-160 символов. Если меньше 120 — добавь характеристики."

        return system_prompt, user_prompt

    def get_ozon_desc_prompt(self, category: str, purposes: List[str],
                             additional_params: List[str], keywords: List[str],
                             category_description: str = "") -> Tuple[str, str]:
        """
        Промпт для генерации SEO-описания Ozon
        """
        title_raw = self._build_title_raw(category, purposes, keywords)
        if category_description and category_description not in title_raw:
            title_raw = f"{category_description} / {title_raw}"

        description_raw = self._build_description_raw(category, purposes, additional_params, keywords)

        system_prompt, user_prompt = self.get_marketplace_content_prompt(title_raw, description_raw)
        user_prompt += "\n\nВерни ТОЛЬКО секцию OZON_FULL_DESCRIPTION, без остальных секций."

        return system_prompt, user_prompt

    # Дополнительный метод для получения всего контента сразу (если понадобится)
    def get_all_content_prompts(self, category: str, purposes: List[str],
                                additional_params: List[str], keywords: List[str]) -> Tuple[str, str]:
        """
        Возвращает промпты для генерации всего контента сразу
        """
        title_raw = self._build_title_raw(category, purposes, keywords)
        description_raw = self._build_description_raw(category, purposes, additional_params, keywords)

        return self.get_marketplace_content_prompt(title_raw, description_raw)

    def parse_all_content(self, result: str) -> dict:
        """
        Парсит результат генерации всех секций
        Возвращает словарь с секциями
        """
        sections = [
            "WB_TITLE",
            "WB_SHORT_TITLE",
            "WB_SHORT_DESCRIPTION",
            "WB_FULL_DESCRIPTION",
            "OZON_TITLE",
            "OZON_FULL_DESCRIPTION"
        ]

        parsed = {}
        for section in sections:
            # Используем новый метод
            parsed[section.lower()] = self.parse_result(result, section)

        return parsed