# app/bot/handlers/content_generation_handler.py
import logging
import hashlib
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Tuple, List, Optional
from app.bot.handlers.base_handler import BaseMessageHandler
from app.utils.logger import log
from app.utils.log_codes import LogCodes


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

        # WB
        self.router.callback_query.register(self.handle_generate_wb_title, F.data.startswith("generate_wb_title_"))
        self.router.callback_query.register(self.handle_generate_wb_short_desc, F.data.startswith("generate_wb_short_"))
        self.router.callback_query.register(self.handle_generate_wb_long_desc, F.data.startswith("generate_wb_long_"))

        # Ozon
        self.router.callback_query.register(self.handle_generate_ozon_title, F.data.startswith("generate_ozon_title_"))
        self.router.callback_query.register(self.handle_generate_ozon_desc, F.data.startswith("generate_ozon_desc_"))

        self.router.callback_query.register(self.handle_back_to_data, F.data.startswith("back_to_data_"))

        # Навигация
        self.router.callback_query.register(self.handle_back_to_generation_menu, F.data == "back_to_generation_menu")

    async def show_generation_menu(self, message: Message, session_id: str):
        """Показать меню генерации контента"""
        builder = InlineKeyboardBuilder()

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
        builder.button(
            text="🛍️ Название Ozon",
            callback_data=f"generate_ozon_title_{session_id}"
        )
        builder.button(
            text="📄 Описание Ozon",
            callback_data=f"generate_ozon_desc_{session_id}"
        )
        builder.button(
            text="↩️ Назад к данным",
            callback_data=f"back_to_data_{session_id}"
        )

        builder.adjust(1)

        log.info(LogCodes.GEN_MENU_SHOW)

        await message.answer(
            "🎯 <b>Меню генерации контента:</b>\n\n"
            "<b>Wildberries:</b>\n"
            "• Заголовок (до 60 символов)\n"
            "• Краткое описание (до 1000 символов)\n"
            "• Полное описание (до 2000 символов)\n\n"
            "<b>Ozon:</b>\n"
            "• SEO-название (120-160 символов)\n"
            "• SEO-описание (1500-3000 символов)",
            reply_markup=builder.as_markup()
        )

    async def handle_back_to_data(self, callback: CallbackQuery):
        """Возврат к данным сессии"""
        log.info(LogCodes.GEN_BACK_TO_DATA)

        try:
            session_id = callback.data.replace("back_to_data_", "")

            session_repo = self.repositories['session_repo']
            session = session_repo.get_by_id(session_id)

            if not session:
                log.warning(LogCodes.ERR_SESSION_NOT_FOUND, id=session_id)
                await callback.answer("❌ Сессия не найдена", show_alert=True)
                return

            # Получаем название категории
            category_name = "Неизвестно"
            if 'category_repo' in self.repositories:
                category_repo = self.repositories['category_repo']
                category = category_repo.get_by_id(session.category_id)
                if category:
                    category_name = category.name

            # Получаем назначения в читаемом виде
            purposes_text = "не указаны"
            if hasattr(session, 'purposes') and session.purposes:
                if isinstance(session.purposes, list):
                    purposes_text = ", ".join(session.purposes)
                else:
                    purposes_text = str(session.purposes)

            additional_params_text = "не указаны"
            if session.additional_params:
                if isinstance(session.additional_params, list):
                    additional_params_text = ", ".join(session.additional_params)
                else:
                    additional_params_text = str(session.additional_params)

            builder = InlineKeyboardBuilder()
            builder.button(
                text="🎯 Меню генерации",
                callback_data=f"show_generation_menu_{session.id}"
            )
            builder.button(
                text="✏️ Ручная фильтрация ключей",
                callback_data=f"manual_filter_{session.id}"
            )
            builder.button(
                text="↩️ Назад к данным",
                callback_data=f"back_to_data_{session_id}"
            )
            builder.adjust(1)

            keywords_preview = "\n".join([f"• {kw}" for kw in session.keywords[:15]])
            if len(session.keywords) > 15:
                keywords_preview += f"\n• ... и ещё {len(session.keywords) - 15}"

            await callback.message.answer(
                f"📊 <b>Собранные данные:</b>\n\n"
                f"📁 <b>Категория:</b> {category_name}\n"
                f"🎯 <b>Назначения:</b> {purposes_text}\n"
                f"📝 <b>Доп. параметры:</b> {additional_params_text}\n\n"
                f"🔑 <b>Ключевые слова ({len(session.keywords)}):</b>\n{keywords_preview}",
                reply_markup=builder.as_markup()
            )

            try:
                await callback.message.delete()
            except:
                pass

            await callback.answer()

        except Exception as e:
            log.error(LogCodes.ERR_HANDLER, handler="back_to_data", error=str(e))
            await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)

    def _has_size_in_params(self, additional_params: List[str], keywords: List[str]) -> bool:
        """Проверяет, есть ли указания на размеры в параметрах или ключевых словах"""
        size_indicators = ['мм', 'см', 'м', 'размер', 'длина', 'ширина', 'высота',
                           'толщина', 'формат', '×', 'x', '*', 'габарит']

        for param in additional_params:
            param_lower = param.lower()
            if any(indicator in param_lower for indicator in size_indicators):
                return True

        for kw in keywords:
            kw_lower = kw.lower()
            if any(indicator in kw_lower for indicator in size_indicators):
                return True

        return False

    def _has_size_mention(self, text: str) -> bool:
        """Проверяет, есть ли в тексте упоминание размеров"""
        size_patterns = ['мм', 'см', 'м', '×', 'x', '*', 'размер', 'формат']
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in size_patterns)

    def _translate_purposes_to_russian(self, purposes: List[str]) -> List[str]:
        """Переводит английские ID назначений в русские названия"""
        if not purposes:
            return []

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
                    found = False
                    for eng_key, rus_value in purpose_map.items():
                        if eng_key in purpose_lower:
                            translated.append(rus_value)
                            found = True
                            break
                    if not found:
                        translated.append(purpose)
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

            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if not category:
                return None, "❌ Категория не найдена"

            keywords = session.keywords or []

            purposes = []
            if hasattr(session, 'purposes') and session.purposes:
                purposes = self._translate_purposes_to_russian(session.purposes)
            elif hasattr(session, 'purpose') and session.purpose:
                purposes = [session.purpose]

            additional_params = session.additional_params or []

            return {
                'session': session,
                'category': category.name,
                'purposes': purposes,
                'additional_params': additional_params,
                'keywords': keywords
            }, None

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=f"Get session data: {e}")
            return None, f"❌ Ошибка: {str(e)}"

    async def _generate_wb_title_with_retry(self, callback: CallbackQuery, session_id: str,
                                            max_retries: int = 3) -> str:
        """Специализированный метод для генерации Wildberries title"""
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

        keywords_with_priority = "\n".join([f"{i + 1}. {kw}" for i, kw in enumerate(keywords[:15])])

        expected_order = """
        Строгий порядок для WB title:
        1. Самый частотный поисковый запрос
        2. Материал (ПВХ если панели)
        3. Назначение
        4. Формат
        5. Размер или количество
        """

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

        return content

    async def _generate_ozon_title_with_retry(self, callback: CallbackQuery, session_id: str,
                                              max_retries: int = 3) -> str:
        """Специализированный метод для генерации Ozon title"""
        data, error = await self._get_session_data(session_id)
        if error:
            await callback.message.answer(error)
            return None

        category = data['category']
        purposes = data['purposes']
        keywords = data['keywords']
        additional_params = data['additional_params']

        has_sizes = self._has_size_in_params(additional_params, keywords)

        prompt_service = self.services.get('prompt')
        openai_service = self.services.get('openai')
        if not prompt_service or not openai_service:
            await callback.message.answer("❌ Сервисы не доступны")
            return None

        category_repo = self.repositories['category_repo']
        category_obj = category_repo.get_by_id(data['session'].category_id)
        category_description = category_obj.description if category_obj else ""

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

            if 120 <= length <= 160:
                break

            retry_count += 1
            has_sizes_in_title = self._has_size_mention(current_content)

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
            else:
                break

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

            if not has_sizes and has_sizes_in_title:
                size_warning = """
                В текущем названии ЕСТЬ указания на размеры, хотя в исходных данных их нет.
                Удали все упоминания размеров.
                """
            else:
                size_warning = ""

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

        return current_content

    async def _generate_content(self, callback: CallbackQuery, session_id: str,
                                generation_type: str, marketplace: str):
        """Общий метод генерации контента"""
        try:
            await callback.answer(f"🔄 Генерирую...")

            log.info(LogCodes.GEN_START, type=generation_type, marketplace=marketplace)

            status_msg = await callback.message.answer(f"🤖 <b>Генерирую контент...</b>")

            try:
                prompt_service = self.services.get('prompt')
                openai_service = self.services.get('openai')

                if not prompt_service or not openai_service:
                    await self._safe_edit_text(status_msg, "❌ Сервисы не доступны")
                    log.error(LogCodes.ERR_OPENAI, error="Services not available")
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

                    start_time = time.time()
                    content = await openai_service.generate_text(
                        prompt=user_prompt,
                        system_prompt=system_prompt,
                        max_tokens=self._get_max_tokens(generation_type, marketplace),
                        temperature=self.config.api.openai_temperature
                    )
                    elapsed = time.time() - start_time

                    log.info(LogCodes.GPT_SUCCESS, time=f"{elapsed:.1f}")

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

                # Сохраняем в БД
                try:
                    session_repo = self.repositories['session_repo']
                    content_repo = self.repositories.get('content_repo')
                    snapshot_repo = self.repositories.get('snapshot_repo')

                    if content_repo:
                        session_context_result = await self._get_session_data(session_id)
                        if session_context_result and session_context_result[0]:
                            session_data = session_context_result[0]

                            content_type_map = {
                                ('title', 'wb'): 'wb_title',
                                ('short_desc', 'wb'): 'wb_short_desc',
                                ('long_desc', 'wb'): 'wb_long_desc',
                                ('title', 'ozon'): 'ozon_title',
                                ('desc', 'ozon'): 'ozon_desc',
                            }
                            key = (generation_type, marketplace)

                            if key in content_type_map:
                                field_name = f"last_generated_{content_type_map[key]}"
                                session_repo.update_session_data(
                                    session_id,
                                    **{field_name: content}
                                )
                                log.info(LogCodes.GEN_SAVE)

                    if snapshot_repo:
                        context_data, _ = await self._get_session_data(session_id)
                        if context_data:
                            session_obj = context_data['session']

                            context = {
                                'user_id': callback.from_user.id,
                                'session_id': session_id,
                                'category_id': session_obj.category_id,
                                'category_name': context_data['category'],
                                'purposes': context_data['purposes'],
                                'additional_params': context_data['additional_params'],
                                'keywords': context_data['keywords'],
                            }

                            content_dict = {
                                'wb_title': content if generation_type == 'title' and marketplace == 'wb' else None,
                                'wb_short_desc': content if generation_type == 'short_desc' and marketplace == 'wb' else None,
                                'wb_long_desc': content if generation_type == 'long_desc' and marketplace == 'wb' else None,
                                'ozon_title': content if generation_type == 'title' and marketplace == 'ozon' else None,
                                'ozon_desc': content if generation_type == 'desc' and marketplace == 'ozon' else None,
                            }

                            snapshot = snapshot_repo.create_snapshot(
                                user_id=callback.from_user.id,
                                session_id=session_id,
                                context=context,
                                content=content_dict,
                                generation_type=generation_type,
                                marketplace=marketplace
                            )
                            log.info(LogCodes.GEN_SNAPSHOT, id=snapshot.id[:8])

                except Exception as e:
                    log.error(LogCodes.ERR_DATABASE, error=str(e))

                await self._safe_delete_message(status_msg)

                result_type = self._get_result_type(generation_type, marketplace)

                builder = InlineKeyboardBuilder()
                builder.button(text="🔄 Сгенерировать заново", callback_data=callback.data)
                builder.button(text="🎯 Меню генерации", callback_data="back_to_generation_menu")
                builder.button(text="↩️ К данным", callback_data=f"back_to_data_{session_id}")
                builder.adjust(1)

                display_text = self._format_output(content, result_type, generation_type, marketplace)
                await callback.message.answer(display_text, reply_markup=builder.as_markup())

                log.info(LogCodes.GEN_SUCCESS, length=len(content))

            except Exception as e:
                error_text = f"❌ Ошибка генерации: {str(e)[:200]}"
                await self._safe_edit_text(status_msg, error_text)
                log.error(LogCodes.ERR_OPENAI, error=str(e))

        except Exception as e:
            log.error(LogCodes.ERR_HANDLER, handler="generate_content", error=str(e))
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
        """
        Форматирует вывод с рекомендациями по длине

        Args:
            content: Сгенерированный контент
            result_type: Тип результата (заголовок, описание и т.д.)
            generation_type: Тип генерации (title, short_desc, long_desc, desc)
            marketplace: Маркетплейс (wb, ozon)

        Returns:
            Отформатированный текст для отправки
        """
        display_text = f"<b>📄 {result_type}:</b>\n\n<code>{content}</code>\n\n"

        length = len(content)
        words_count = len(content.split())

        # Базовый вывод длины
        display_text += f"📏 <b>Длина:</b> {length} символов"

        # Добавляем количество слов для заголовков
        if generation_type == "title":
            display_text += f" | <b>Слов:</b> {words_count}"

        # Добавляем рекомендации в зависимости от типа контента
        recommendations = {
            ('title', 'wb'): "60-80 символов",
            ('title', 'ozon'): "120-160 символов",
            ('short_desc', 'wb'): "до 1000 символов",
            ('long_desc', 'wb'): "1500-2200 символов",
            ('desc', 'ozon'): "1500-3000 символов",
        }

        key = (generation_type, marketplace)
        if key in recommendations:
            display_text += f"\n💡 <b>Рекомендация:</b> {recommendations[key]}"

        return display_text

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
            user_id = callback.from_user.id
            session_repo = self.repositories['session_repo']
            session = session_repo.get_active_session(user_id)

            if session:
                await self.show_generation_menu(callback.message, session.id)
                await callback.message.delete()
            else:
                await callback.answer("❌ Сессия не найдена")
        except Exception as e:
            log.error(LogCodes.ERR_HANDLER, handler="back_to_generation_menu", error=str(e))
            await callback.answer("❌ Ошибка возврата")