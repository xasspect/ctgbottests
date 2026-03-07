# app/bot/handlers/content_generation_handler.py
import logging
import hashlib
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Tuple, List, Optional
from app.bot.handlers.base_handler import BaseMessageHandler


class ContentGenerationHandler(BaseMessageHandler):
    """Обработчик генерации контента для WB и Ozon"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()
        self.logger = logging.getLogger(__name__)
        # Хранилище для сгенерированного контента (чтобы можно было копировать)
        self.generated_content = {}

    async def register(self, dp):
        """Регистрация обработчиков"""
        dp.include_router(self.router)

        # Кнопки генерации Wildberries
        self.router.callback_query.register(
            self.handle_generate_wb_title,
            F.data.startswith("generate_wb_title_")
        )
        self.router.callback_query.register(
            self.handle_generate_wb_short_desc,
            F.data.startswith("generate_wb_short_")
        )
        self.router.callback_query.register(
            self.handle_generate_wb_long_desc,
            F.data.startswith("generate_wb_long_")
        )

        # Кнопки генерации Ozon
        self.router.callback_query.register(
            self.handle_generate_ozon_title,
            F.data.startswith("generate_ozon_title_")
        )
        self.router.callback_query.register(
            self.handle_generate_ozon_desc,
            F.data.startswith("generate_ozon_desc_")
        )

        self.router.callback_query.register(
            self.handle_back_to_data,  # НОВЫЙ обработчик
            F.data == "back_to_results"
        )

        # Навигация
        self.router.callback_query.register(
            self.handle_back_to_generation_menu,
            F.data == "back_to_generation_menu"
        )

    async def show_generation_menu(self, message: Message, session_id: str):
        """Показать меню генерации контента (в новом сообщении)"""
        builder = InlineKeyboardBuilder()

        # Кнопки Wildberries
        builder.button(
            text="📝 Заголовок Wildberries",
            callback_data=f"generate_wb_title_{session_id}"
        )
        builder.button(
            text="📋 Краткое описание Wildberries",
            callback_data=f"generate_wb_short_{session_id}"
        )
        builder.button(
            text="📖 Полное описание Wildberries",
            callback_data=f"generate_wb_long_{session_id}"
        )

        # Кнопки Ozon
        builder.button(
            text="🛍️ Название Ozon",
            callback_data=f"generate_ozon_title_{session_id}"
        )
        builder.button(
            text="📄 Описание Ozon",
            callback_data=f"generate_ozon_desc_{session_id}"
        )

        # Кнопка возврата к данным (оставляем, но она будет в новом сообщении)
        builder.button(
            text="↩️ Назад к данным",
            callback_data=f"back_to_data_{session_id}"
        )

        builder.adjust(1)

        # ИЗМЕНЕНО: отправляем новое сообщение вместо редактирования старого
        await message.answer(
            "🎯 <b>Меню генерации контента:</b>\n\n"
            "<b>Wildberries:</b>\n"
            "• Заголовок (до 60 символов)\n"
            "• Краткое описание (до 1000 символов)\n"
            "• Полное описание (до 2000 символов)\n\n"
            "<b>Ozon:</b>\n"
            "• SEO-название (120-160 символов)\n"
            "• SEO-описание (1500-3000 символов)\n\n"
            "<i>Нажмите «Назад к данным» чтобы вернуться к собранным ключевым словам</i>",
            reply_markup=builder.as_markup()
        )

    async def handle_back_to_data(self, callback: CallbackQuery):
        """Возврат к данным сессии (в новом сообщении)"""
        try:
            session_id = callback.data.replace("back_to_data_", "")
            session_repo = self.repositories['session_repo']
            session = session_repo.get_by_id(session_id)

            if not session:
                await callback.answer("❌ Сессия не найдена")
                return

            # Получаем название категории
            category_name = "Неизвестно"
            if 'category_repo' in self.repositories:
                category_repo = self.repositories['category_repo']
                category = category_repo.get_by_id(session.category_id)
                if category:
                    category_name = category.name

            # Формируем клавиатуру для данных
            builder = InlineKeyboardBuilder()
            builder.button(
                text="🎯 Меню генерации",
                callback_data=f"show_generation_menu_{session.id}"
            )
            builder.button(
                text="✏️ Ручная фильтрация ключей",
                callback_data=f"manual_filter_{session.id}"
            )
            builder.adjust(1)

            # Превью ключевых слов
            preview = "\n".join([f"• {kw}" for kw in session.keywords[:15]])
            if len(session.keywords) > 15:
                preview += f"\n• ... и ещё {len(session.keywords) - 15}"

            # Отправляем новое сообщение с данными
            await callback.message.answer(
                f"📊 <b>Собранные данные:</b>\n\n"
                f"📁 <b>Категория:</b> {category_name}\n"
                f"🔑 <b>Ключевых слов:</b> {len(session.keywords)}\n\n"
                f"<b>Ключевые слова:</b>\n{preview}",
                reply_markup=builder.as_markup()
            )

            # Удаляем сообщение с меню генерации (опционально)
            await callback.message.delete()

            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при возврате к данным: {e}")
            await callback.answer("❌ Ошибка", show_alert=True)

    # async def handle_copy_content(self, callback: CallbackQuery):
    #     """Обработка кнопки копирования контента"""
    #     try:
    #         # Извлекаем ID контента из callback_data
    #         content_id = callback.data.replace("copy_", "")
    #
    #         # Получаем сохранённый контент
    #         content_data = self.generated_content.get(content_id)
    #
    #         if not content_data:
    #             await callback.answer("❌ Контент не найден или устарел", show_alert=True)
    #             return
    #
    #         # Отправляем контент отдельным сообщением для удобного копирования
    #         await callback.message.answer(
    #             f"<b>📋 {content_data['type']} (для копирования):</b>\n\n"
    #             f"<code>{content_data['content']}</code>"
    #         )
    #
    #         await callback.answer("✅ Контент скопирован в сообщение выше", show_alert=False)
    #
    #     except Exception as e:
    #         self.logger.error(f"Ошибка при копировании: {e}")
    #         await callback.answer("❌ Ошибка при копировании", show_alert=True)

    # def _save_content_for_copy(self, content: str, content_type: str) -> str:
    #     """
    #     Сохраняет контент для возможности копирования
    #     Возвращает ID контента
    #     """
    #     # Создаём уникальный ID на основе контента и времени
    #     content_id = hashlib.md5(f"{content}{content_type}{time.time()}".encode()).hexdigest()[:8]
    #
    #     self.generated_content[content_id] = {
    #         'content': content,
    #         'type': content_type,
    #         'timestamp': time.time()
    #     }
    #
    #     # Очищаем старые записи (старше 1 часа)
    #     current_time = time.time()
    #     self.generated_content = {
    #         k: v for k, v in self.generated_content.items()
    #         if current_time - v['timestamp'] < 3600
    #     }
    #
    #     return content_id

    def _has_size_in_params(self, additional_params: List[str], keywords: List[str]) -> bool:
        """
        Проверяет, есть ли указания на размеры в параметрах или ключевых словах
        """
        size_indicators = ['мм', 'см', 'м', 'размер', 'длина', 'ширина', 'высота',
                           'толщина', 'формат', '×', 'x', '*', 'габарит']

        # Проверяем дополнительные параметры
        for param in additional_params:
            param_lower = param.lower()
            if any(indicator in param_lower for indicator in size_indicators):
                return True

        # Проверяем ключевые слова
        for kw in keywords:
            kw_lower = kw.lower()
            if any(indicator in kw_lower for indicator in size_indicators):
                return True

        return False

    def _has_size_mention(self, text: str) -> bool:
        """
        Проверяет, есть ли в тексте упоминание размеров
        """
        size_patterns = ['мм', 'см', 'м', '×', 'x', '*', 'размер', 'формат']
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in size_patterns)

    def _translate_purposes_to_russian(self, purposes: List[str]) -> List[str]:
        """
        Переводит английские ID назначений в русские названия
        """
        if not purposes:
            return []

        # Маппинг назначений на русский (такой же как в скрапере)
        purpose_map = {
            "wood": "под дерево",
            "with_pattern": "с рисунком",
            "kitchen": "кухня",
            "tile": "плитка",
            "3d": "3D",
            "in_roll": "в рулоне",
            "self_adhesive": "самоклеящиеся",
            "stone": "под камень",
            "bathroom": "ванная",
            "bedroom": "спальня",
            "brick": "под кирпич",
            "marble": "под мрамор",
            "living_room": "гостиная",
            "white": "белый"
        }

        translated = []
        for purpose in purposes:
            if isinstance(purpose, str):
                purpose_lower = purpose.lower()
                if purpose_lower in purpose_map:
                    translated.append(purpose_map[purpose_lower])
                else:
                    # Проверяем частичное совпадение
                    found = False
                    for eng_key, rus_value in purpose_map.items():
                        if eng_key in purpose_lower:
                            translated.append(rus_value)
                            found = True
                            break
                    if not found:
                        translated.append(purpose)  # оставляем как есть
            else:
                translated.append(str(purpose))

        return translated

    async def _get_session_data(self, session_id: str):
        """Получить данные сессии и ключевые слова"""
        try:
            session_repo = self.repositories['session_repo']
            session = session_repo.get_by_id(session_id)

            if not session:
                return None, "❌ Сессия не найдена"

            # Получаем категорию
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if not category:
                return None, "❌ Категория не найдена"

            # Получаем ключевые слова из сессии
            keywords = session.keywords or []

            # Получаем назначения
            purposes = []
            if hasattr(session, 'purposes') and session.purposes:
                # ДОБАВЛЯЕМ ПЕРЕВОД НАЗНАЧЕНИЙ!
                purposes = self._translate_purposes_to_russian(session.purposes)
            elif hasattr(session, 'purpose') and session.purpose:
                purposes = [session.purpose]

            # Получаем дополнительные параметры
            additional_params = session.additional_params or []

            return {
                'session': session,
                'category': category.name,
                'purposes': purposes,  # Здесь уже переведенные на русский
                'additional_params': additional_params,
                'keywords': keywords
            }, None

        except Exception as e:
            self.logger.error(f"Ошибка получения данных сессии: {e}")
            return None, f"❌ Ошибка: {str(e)}"

    async def _generate_wb_title_with_retry(self, callback: CallbackQuery, session_id: str,
                                            max_retries: int = 3) -> str:
        """
        Специализированный метод для генерации Wildberries title с контролем длины
        и соответствием порядку ключевых слов
        """
        data, error = await self._get_session_data(session_id)
        if error:
            await callback.message.answer(error)
            return None

        category = data['category']
        purposes = data['purposes']
        keywords = data['keywords']
        additional_params = data['additional_params']

        prompt_service = self.services.get('prompt')
        openai_service = self.services.get('openai')
        if not prompt_service or not openai_service:
            await callback.message.answer("❌ Сервисы не доступны")
            return None

        # Формируем подсказку о порядке ключевых слов
        keywords_with_priority = "\n".join([f"{i + 1}. {kw}" for i, kw in enumerate(keywords[:15])])

        expected_order = """
        Строгий порядок для WB title:
        1. Самый частотный поисковый запрос
        2. Материал (ПВХ если панели)
        3. Назначение
        4. Формат
        5. Размер или количество
        """

        # Первый запрос
        system_prompt, user_prompt = prompt_service.get_wb_title_prompt(
            category=category, purposes=purposes,
            additional_params=additional_params, keywords=keywords
        )

        user_prompt += f"""

        Приоритет ключевых слов:
        {keywords_with_priority}

        {expected_order}

        Используй ключевые слова в порядке их приоритета.
        """

        content = await openai_service.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=400,
            temperature=self.config.api.openai_temperature
        )

        # ИСПРАВЛЕНИЕ: Не проверяем длину здесь, просто возвращаем сырой ответ
        # Проверка длины будет после парсинга в _generate_content

        return content

    async def _generate_ozon_title_with_retry(self, callback: CallbackQuery, session_id: str,
                                              max_retries: int = 3) -> str:
        """
        Специализированный метод для генерации Ozon title с контролем длины
        """
        data, error = await self._get_session_data(session_id)
        if error:
            await callback.message.answer(error)
            return None

        category = data['category']
        purposes = data['purposes']
        keywords = data['keywords']
        additional_params = data['additional_params']

        # Проверяем, есть ли размеры во входных данных
        has_sizes = self._has_size_in_params(additional_params, keywords)

        prompt_service = self.services.get('prompt')
        openai_service = self.services.get('openai')
        if not prompt_service or not openai_service:
            await callback.message.answer("❌ Сервисы не доступны")
            return None

        # Получаем описание категории
        category_repo = self.repositories['category_repo']
        category_obj = category_repo.get_by_id(data['session'].category_id)
        category_description = category_obj.description if category_obj else ""

        # Первый запрос
        system_prompt, user_prompt = prompt_service.get_ozon_title_prompt(
            category=category, purposes=purposes,
            additional_params=additional_params, keywords=keywords,
            category_description=category_description
        )

        content = await openai_service.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=200,
            temperature=self.config.api.openai_temperature
        )

        retry_count = 0
        current_content = content

        while retry_count < max_retries:
            length = len(current_content)

            # Проверяем длину
            if 120 <= length <= 160:
                self.logger.info(f"✅ Ozon title в норме: {length} символов")
                break

            retry_count += 1

            # Проверяем наличие размеров в текущем названии
            has_sizes_in_title = self._has_size_mention(current_content)

            # Формируем базовый промпт в зависимости от проблемы
            if length < 120:
                base_prompt = f"""
                Название содержит {length} символов. Нужно минимум 120, но не больше 160. Расширь.

                Исходное название: {current_content}

                Исходные данные:
                Категория: {category}
                Назначения: {', '.join(purposes)}
                Ключевые слова: {', '.join(keywords[:20])}
                """
                action = "расширь"
            elif length > 160:
                base_prompt = f"""
                Название содержит {length} символов. Нужно минимум 120, но не больше 160. Укороти.

                Исходное название: {current_content}

                Исходные данные:
                Категория: {category}
                Назначения: {', '.join(purposes)}
                Ключевые слова: {', '.join(keywords[:10])}
                """
                action = "укороти"

            # Добавляем правило про размеры
            if not has_sizes:
                size_rule = """
                ВАЖНО: В исходных данных НЕТ указаний на размеры товара.
                НЕ ДОБАВЛЯЙ никаких размеров (мм, см, м, × и т.д.) в название.
                Используй только характеристики из ключевых слов.
                """
            else:
                size_rule = """
                В исходных данных ЕСТЬ указания на размеры.
                Можешь использовать размеры для расширения названия, если нужно.
                """

            # Проверяем, есть ли сейчас размеры в названии (для случая, когда их быть не должно)
            if not has_sizes and has_sizes_in_title:
                size_warning = """
                В текущем названии ЕСТЬ указания на размеры, хотя в исходных данных их нет.
                Удали все упоминания размеров.
                """
            else:
                size_warning = ""

            # Собираем полный промпт
            expand_prompt = base_prompt + size_rule + size_warning + f"""

            Требования:
            - строго 120-160 символов (сейчас {length})
            - сохрани главный поисковый запрос в начале
            - используй только факты из исходных данных
            - никаких маркетинговых слов
            - естественное звучание

            Верни ТОЛЬКО {'расширенное' if action == 'расширь' else 'сокращённое'} название, без пояснений.
            """

            expand_system = f"Ты — SEO-специалист по Ozon. {action.capitalize()}ешь название товара до нужной длины."

            current_content = await openai_service.generate_text(
                prompt=expand_prompt,
                system_prompt=expand_system,
                max_tokens=200,
                temperature=self.config.api.openai_temperature
            )

            self.logger.info(f"Попытка {retry_count}: {len(current_content)} символов")

        return current_content

    async def _generate_content(self, callback: CallbackQuery, session_id: str,
                                generation_type: str, marketplace: str):
        """Общий метод генерации контента"""
        try:
            await callback.answer(f"🔄 Генерирую...")

            status_msg = await callback.message.answer(f"🤖 <b>Генерирую контент...</b>")

            try:
                # Получаем сервисы
                prompt_service = self.services.get('prompt')
                openai_service = self.services.get('openai')

                if not prompt_service or not openai_service:
                    await self._safe_edit_text(status_msg, "❌ Сервисы не доступны")
                    return

                # Генерируем контент
                if generation_type == "title":
                    if marketplace == "ozon":
                        content = await self._generate_ozon_title_with_retry(callback, session_id, max_retries=3)
                    elif marketplace == "wb":
                        content = await self._generate_wb_title_with_retry(callback, session_id, max_retries=3)
                    else:
                        content = None
                else:
                    data, error = await self._get_session_data(session_id)
                    if error:
                        await self._safe_edit_text(status_msg, error)
                        return

                    system_prompt, user_prompt = self._get_prompt(
                        prompt_service, generation_type, marketplace,
                        data['category'], data['purposes'], data['keywords']
                    )

                    if not system_prompt:
                        await self._safe_edit_text(status_msg, "❌ Не удалось получить промпт")
                        return

                    content = await openai_service.generate_text(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        max_tokens=self._get_max_tokens(generation_type, marketplace),
                        temperature=self.config.api.openai_temperature
                    )

                if content is None:
                    await self._safe_edit_text(status_msg, "❌ Ошибка генерации")
                    return

                # Парсим результат
                section_map = {
                    ("title", "wb"): "WB_TITLE",
                    ("short_desc", "wb"): "WB_SHORT_DESCRIPTION",
                    ("long_desc", "wb"): "WB_FULL_DESCRIPTION",
                    ("title", "ozon"): "OZON_TITLE",
                    ("desc", "ozon"): "OZON_FULL_DESCRIPTION",
                }
                section_key = (generation_type, marketplace)
                if section_key in section_map:
                    section_name = section_map[section_key]
                    parsed_content = prompt_service.parse_result(content, section_name)
                    if parsed_content and parsed_content != content:
                        content = parsed_content
                        self.logger.info(f"✅ Извлечена секция {section_name}")
                    else:
                        self.logger.warning(f"⚠️ Секция {section_name} не найдена, использую весь ответ")

                # Для заголовков делаем повторную проверку длины после парсинга
                if generation_type == "title":
                    length = len(content)
                    self.logger.info(f"📏 Длина после парсинга: {length} символов")

                    # Если длина выходит за пределы, делаем повторную генерацию
                    needs_correction = False
                    if marketplace == "wb" and (length < 60 or length > 80):
                        needs_correction = True
                        target_min, target_max = 60, 80
                    elif marketplace == "ozon" and (length < 120 or length > 160):
                        needs_correction = True
                        target_min, target_max = 120, 160

                    if needs_correction:
                        self.logger.warning(
                            f"⚠️ {marketplace.upper()} title после парсинга {length} символов, требуется корректировка")

                        # Получаем данные сессии для повторной генерации
                        data, error = await self._get_session_data(session_id)
                        if not error:
                            # Формируем промпт для корректировки
                            correction_prompt = f"""
                            Откорректируй заголовок до длины {target_min}-{target_max} символов.

                            Исходный заголовок: {content}

                            Категория: {data['category']}
                            Назначения: {', '.join(data['purposes'])}
                            Ключевые слова: {', '.join(data['keywords'][:10])}

                            Требования:
                            - строго {target_min}-{target_max} символов (сейчас {length})
                            - сохрани смысл и основные ключевые слова
                            - не добавляй маркетинговые слова
                            - без знаков препинания

                            Верни ТОЛЬКО исправленный заголовок.
                            """

                            corrected = await openai_service.generate_text(
                                prompt=correction_prompt,
                                system_prompt=f"Ты SEO-специалист по {marketplace.upper()}. Корректируешь длину заголовка.",
                                max_tokens=100,
                                temperature=0.5
                            )

                            if corrected and target_min <= len(corrected) <= target_max:
                                content = corrected
                                self.logger.info(f"✅ Заголовок скорректирован: {len(content)} символов")

                # ИСПРАВЛЕНИЕ: Безопасно удаляем статусное сообщение
                await self._safe_delete_message(status_msg)

                result_type = self._get_result_type(generation_type, marketplace)

                # Сохраняем контент для копирования
                # content_id = self._save_content_for_copy(content, result_type)

                # Клавиатура после генерации
                builder = InlineKeyboardBuilder()
                builder.button(text="🔄 Сгенерировать заново", callback_data=callback.data)
                # builder.button(text="📋 Скопировать", callback_data=f"copy_{content_id}")
                builder.button(text="🎯 Меню генерации", callback_data="back_to_generation_menu")
                builder.button(text="↩️ К данным", callback_data=f"back_to_data_{session_id}")
                builder.adjust(1)

                # Форматируем вывод
                display_text = self._format_output(content, result_type, generation_type, marketplace)
                await callback.message.answer(display_text, reply_markup=builder.as_markup())

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Безопасно обрабатываем ошибку с статусным сообщением
                error_text = f"❌ Ошибка генерации: {str(e)[:200]}"
                await self._safe_edit_text(status_msg, error_text)
                self.logger.error(f"Ошибка генерации: {e}")

        except Exception as e:
            self.logger.error(f"Ошибка в _generate_content: {e}")
            try:
                await callback.message.answer(f"❌ Ошибка: {str(e)[:200]}")
            except:
                pass

    async def _safe_delete_message(self, message: Message):
        """Безопасно удаляет сообщение"""
        try:
            if message:
                await message.delete()
        except Exception as e:
            self.logger.debug(f"Не удалось удалить сообщение: {e}")

    async def _safe_edit_text(self, message: Message, text: str, **kwargs):
        """Безопасно редактирует текст сообщения"""
        try:
            if message:
                await message.edit_text(text, **kwargs)
        except Exception as e:
            self.logger.debug(f"Не удалось отредактировать сообщение: {e}")
            try:
                # Если не удалось отредактировать, отправляем новое
                await message.answer(text, **kwargs)
            except:
                pass

    def _get_prompt(self, prompt_service, generation_type: str, marketplace: str,
                    category: str, purposes: List[str], keywords: List[str]) -> Tuple[str, str]:
        """Получает соответствующий промпт"""
        if generation_type == "title" and marketplace == "wb":
            return prompt_service.get_wb_title_prompt(
                category=category, purposes=purposes, additional_params=[], keywords=keywords
            )
        elif generation_type == "short_desc" and marketplace == "wb":
            return prompt_service.get_wb_short_desc_prompt(
                category=category, purposes=purposes, additional_params=[], keywords=keywords
            )
        elif generation_type == "long_desc" and marketplace == "wb":
            return prompt_service.get_wb_long_desc_prompt(
                category=category, purposes=purposes, additional_params=[], keywords=keywords
            )
        elif generation_type == "title" and marketplace == "ozon":
            return prompt_service.get_ozon_title_prompt(
                category=category, purposes=purposes, additional_params=[], keywords=keywords,
                category_description=category
            )
        elif generation_type == "desc" and marketplace == "ozon":
            return prompt_service.get_ozon_desc_prompt(
                category=category, purposes=purposes, additional_params=[], keywords=keywords,
                category_description=category
            )
        return None, None

    def _get_max_tokens(self, generation_type: str, marketplace: str) -> int:
        """Возвращает максимальное количество токенов для типа генерации"""
        if generation_type == "title":
            return 200
        elif generation_type == "short_desc":
            return 600
        elif generation_type == "long_desc" or (generation_type == "desc" and marketplace == "ozon"):
            return 1200
        return 200

    def _get_result_type(self, generation_type: str, marketplace: str) -> str:
        """Возвращает название типа результата для отображения"""
        if generation_type == "title" and marketplace == "wb":
            return "заголовок Wildberries"
        elif generation_type == "short_desc" and marketplace == "wb":
            return "краткое описание Wildberries"
        elif generation_type == "long_desc" and marketplace == "wb":
            return "полное описание Wildberries"
        elif generation_type == "title" and marketplace == "ozon":
            return "SEO-название Ozon"
        elif generation_type == "desc" and marketplace == "ozon":
            return "SEO-описание Ozon"
        return "контент"

    def _format_output(self, content: str, result_type: str,
                       generation_type: str, marketplace: str) -> str:
        """Форматирует вывод с учётом типа контента"""

        # Для ВСЕХ типов контента используем code тег для удобного копирования
        display_text = f"<b>📄 {result_type}:</b>\n\n<code>{content}</code>\n\n"
        display_text += f"📏 <b>Длина:</b> {len(content)} символов"

        # Для заголовков добавляем дополнительную информацию
        if generation_type == "title":
            # Показываем статус длины в зависимости от маркетплейса
            if marketplace == "ozon":
                length = len(content)
                if length < 120:
                    display_text += f" ⚠️ <b>МЕНЬШЕ МИНИМУМА!</b> (нужно 120-160)"
                elif length > 160:
                    display_text += f" ⚠️ <b>БОЛЬШЕ МАКСИМУМА!</b> (нужно 120-160)"
                else:
                    display_text += f" ✅ <b>В норме</b> (120-160)"
            elif marketplace == "wb":
                length = len(content)
                if length < 60:
                    display_text += f" ⚠️ <b>МЕНЬШЕ МИНИМУМА!</b> (нужно 60-80)"
                elif length > 80:
                    display_text += f" ⚠️ <b>БОЛЬШЕ МАКСИМУМА!</b> (нужно 60-80)"
                else:
                    display_text += f" ✅ <b>В норме</b> (60-80)"

            display_text += f"\n🔤 <b>Слов:</b> {len(content.split())}"

        return display_text

    # Обработчики для каждой кнопки
    async def handle_generate_wb_title(self, callback: CallbackQuery):
        session_id = callback.data.replace("generate_wb_title_", "")
        await self._generate_content(callback, session_id, "title", "wb")

    async def handle_generate_wb_short_desc(self, callback: CallbackQuery):
        session_id = callback.data.replace("generate_wb_short_", "")
        await self._generate_content(callback, session_id, "short_desc", "wb")

    async def handle_generate_wb_long_desc(self, callback: CallbackQuery):
        session_id = callback.data.replace("generate_wb_long_", "")
        await self._generate_content(callback, session_id, "long_desc", "wb")

    async def handle_generate_ozon_title(self, callback: CallbackQuery):
        session_id = callback.data.replace("generate_ozon_title_", "")
        await self._generate_content(callback, session_id, "title", "ozon")

    async def handle_generate_ozon_desc(self, callback: CallbackQuery):
        session_id = callback.data.replace("generate_ozon_desc_", "")
        await self._generate_content(callback, session_id, "desc", "ozon")

    async def handle_back_to_generation_menu(self, callback: CallbackQuery):
        """Возврат к меню генерации"""
        try:
            # Получаем session_id из активной сессии пользователя
            user_id = callback.from_user.id
            session_repo = self.repositories['session_repo']
            session = session_repo.get_active_session(user_id)

            if session:
                await self.show_generation_menu(callback.message, session.id)
                # Удаляем старое сообщение с результатом генерации
                await callback.message.delete()
            else:
                await callback.answer("❌ Сессия не найдена")
        except Exception as e:
            self.logger.error(f"Ошибка возврата в меню генерации: {e}")
            await callback.answer("❌ Ошибка возврата")

    # async def handle_back_to_set(self, callback: CallbackQuery):
    #     """Возврат к набору данных"""
    #     # Здесь будет переход к отображению собранных данных
    #     from app.bot.handlers.generation_handler import GenerationHandler
    #     gen_handler = GenerationHandler(self.config, self.services, self.repositories)
    #
    #     user_id = callback.from_user.id
    #     session_repo = self.repositories['session_repo']
    #     session = session_repo.get_active_session(user_id)
    #
    #     if session:
    #         # Показываем данные сессии
    #         builder = InlineKeyboardBuilder()
    #         builder.button(
    #             text="🎯 Меню генерации",
    #             callback_data=f"show_generation_menu_{session.id}"
    #         )
    #         builder.button(
    #             text="✏️ Ручная фильтрация ключей",
    #             callback_data=f"manual_filter_{session.id}"
    #         )
    #         builder.adjust(1)
    #
    #         preview = "\n".join([f"• {kw}" for kw in session.keywords[:10]])
    #         if len(session.keywords) > 10:
    #             preview += f"\n• ... и ещё {len(session.keywords) - 10}"
    #
    #         await callback.message.edit_text(
    #             f"📊 <b>Собранные данные:</b>\n\n"
    #             f"• Категория: {session.category_id}\n"
    #             f"• Ключевых слов: {len(session.keywords)}\n\n"
    #             f"<b>Ключевые слова:</b>\n{preview}",
    #             reply_markup=builder.as_markup()
    #         )
    #     else:
    #         await callback.message.answer("❌ Сессия не найдена")
    #
    #     await callback.answer()