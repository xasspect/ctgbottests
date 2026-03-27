# app/bot/handlers/manual_filter_handler.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.base_handler import BaseMessageHandler
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class FilterStates(StatesGroup):
    """Состояния для FSM"""
    waiting_for_keywords = State()  # Ожидание ввода ключевых слов


class ManualFilterHandler(BaseMessageHandler):
    """Обработчик ручной фильтрации ключевых слов"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()
        self.filter_sessions = {}
        # Хранилище ID сообщений с интерфейсом фильтрации
        self.filter_messages = {}  # {session_id: message_id}

    async def register(self, dp):
        """Регистрация обработчиков"""
        dp.include_router(self.router)

        log.info(LogCodes.SYS_INIT, module="ManualFilterHandler")

        # Основные callback'и
        self.router.callback_query.register(
            self.start_manual_filter,
            F.data.startswith("manual_filter_")
        )
        self.router.callback_query.register(
            self.toggle_keyword,
            F.data.startswith("mf_toggle_")
        )
        self.router.callback_query.register(
            self.finish_manual_filter,
            F.data == "mf_done"
        )
        self.router.callback_query.register(
            self.cancel_manual_filter,
            F.data.startswith("mf_cancel_")
        )

        # Упрощенный обработчик добавления ключевых слов
        self.router.callback_query.register(
            self.start_add_keywords_direct,
            F.data.startswith("mf_add_")
        )

        # Обработчик возврата к фильтрации
        self.router.callback_query.register(
            self.back_to_filter,
            F.data.startswith("mf_back_")
        )

        # Обработчик сообщений с новыми ключевыми словами
        self.router.message.register(
            self.process_added_keywords,
            FilterStates.waiting_for_keywords
        )

        log.info(LogCodes.SYS_INIT, module="ManualFilterHandler ready")

    async def start_manual_filter(self, callback: CallbackQuery, state: FSMContext):
        """Начать ручную фильтрацию ключевых слов"""
        log.info(LogCodes.FLT_START)

        await state.clear()

        session_id = callback.data.replace("manual_filter_", "")
        log.info(f"Filter session_id: {session_id}")

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            log.warning(LogCodes.ERR_SESSION_NOT_FOUND, id=session_id)
            await callback.answer("❌ Сессия не найдена", show_alert=True)
            return

        if not session.keywords:
            session.keywords = []
            session_repo.update(session.id, keywords=[])

        self.filter_sessions[session_id] = {
            'keywords': session.keywords.copy(),
            'excluded': []
        }

        # Сохраняем ID сообщения с интерфейсом фильтрации
        self.filter_messages[session_id] = callback.message.message_id

        await self.show_filter_interface(callback.message, session_id)
        await callback.answer()

    async def show_filter_interface(self, message: Message, session_id: str):
        """Показать интерфейс фильтрации"""
        filter_data = self.filter_sessions.get(session_id)

        if not filter_data:
            await message.edit_text("❌ Сессия фильтрации не найдена")
            return

        keywords = filter_data['keywords']
        excluded = filter_data['excluded']

        builder = InlineKeyboardBuilder()

        # Показываем ключевые слова с чекбоксами (максимум 30)
        for i, keyword in enumerate(keywords[:30]):
            status = "✅" if i not in excluded else "❌"
            builder.button(
                text=f"{status} {keyword}",
                callback_data=f"mf_toggle_{session_id}_{i}"
            )

        # Кнопки управления
        builder.button(text="➕ Добавить ключевые слова", callback_data=f"mf_add_{session_id}")
        builder.button(text="✅ Завершить", callback_data="mf_done")
        builder.button(text="❌ Отмена", callback_data=f"mf_cancel_{session_id}")
        builder.adjust(1)

        selected_count = len(keywords) - len(excluded)

        # Формируем текст со списком ключевых слов
        keywords_text = ""
        if keywords:
            keywords_list = []
            for i, kw in enumerate(keywords):
                status_icon = "✅" if i not in excluded else "❌"
                keywords_list.append(f"{status_icon} {kw}")
            keywords_text = "\n".join(keywords_list[:20])
            if len(keywords) > 20:
                keywords_text += f"\n... и ещё {len(keywords) - 20} слов"
        else:
            keywords_text = "Ключевые слова отсутствуют"

        await message.edit_text(
            f"✏️ <b>Ручная фильтрация ключевых слов</b>\n\n"
            f"Всего слов: {len(keywords)}\n"
            f"Выбрано: {selected_count}\n"
            f"Исключено: {len(excluded)}\n\n"
            f"<b>Ключевые слова:</b>\n{keywords_text}\n\n"
            f"✅ — слово будет использоваться\n"
            f"❌ — слово исключено\n"
            f"➕ — добавить новые ключевые слова\n\n"
            f"<i>Нажмите на слово, чтобы изменить статус.</i>",
            reply_markup=builder.as_markup()
        )

    async def start_add_keywords_direct(self, callback: CallbackQuery, state: FSMContext):
        """Сразу переводим пользователя в режим ввода ключевых слов"""
        session_id = callback.data.replace("mf_add_", "")
        log.info(f"Start add keywords for session: {session_id}")

        # Очищаем предыдущее состояние
        await state.clear()

        # Сохраняем session_id в состоянии
        await state.update_data(
            filter_session_id=session_id,
            filter_message_id=callback.message.message_id  # Сохраняем ID сообщения с фильтрацией
        )
        await state.set_state(FilterStates.waiting_for_keywords)

        log.info(f"FSM state set to: {await state.get_state()}")

        # Показываем сообщение с инструкцией и кнопкой отмены
        builder = InlineKeyboardBuilder()
        builder.button(
            text="↩️ Отмена",
            callback_data=f"mf_back_{session_id}"
        )
        builder.adjust(1)

        # Редактируем текущее сообщение, чтобы показать форму ввода
        await callback.message.edit_text(
            f"✏️ <b>Введите ключевые слова</b>\n\n"
            f"Отправьте список ключевых слов через запятую.\n\n"
            f"<i>Например: пвх, влагостойкие, 3д, белые, под камень</i>\n\n"
            f"Слова будут добавлены к существующему списку.\n\n"
            f"<b>После ввода вы вернетесь к фильтрации.</b>",
            reply_markup=builder.as_markup()
        )
        await callback.answer()

    async def process_added_keywords(self, message: Message, state: FSMContext):
        """Обработать введенные ключевые слова и сразу вернуться к фильтрации"""
        log.info("=== process_added_keywords ===")
        log.info(f"Message text: {message.text[:100] if message.text else 'None'}")

        # Проверяем текущее состояние
        current_state = await state.get_state()
        log.info(f"Current FSM state: {current_state}")

        if current_state != FilterStates.waiting_for_keywords:
            log.warning(f"Wrong state: {current_state}, ignoring")
            return

        # Получаем данные из состояния
        state_data = await state.get_data()
        session_id = state_data.get('filter_session_id')
        filter_message_id = state_data.get('filter_message_id')

        log.info(f"Session ID from state: {session_id}")
        log.info(f"Filter message ID from state: {filter_message_id}")

        if not session_id:
            log.warning("No session_id in state")
            await message.answer("❌ Сессия не найдена. Начните заново.")
            await state.clear()
            return

        # Получаем данные фильтрации из памяти
        filter_data = self.filter_sessions.get(session_id)
        log.info(f"Filter data exists: {filter_data is not None}")

        if not filter_data:
            log.warning(f"Filter session not found: {session_id}")
            await message.answer("❌ Сессия фильтрации не найдена")
            await state.clear()
            return

        # Парсим введенные ключевые слова
        input_text = message.text.strip()

        # Разделяем по запятой и очищаем
        new_keywords = []
        for kw in input_text.split(','):
            kw_clean = kw.strip().lower()
            if kw_clean and kw_clean not in new_keywords:
                new_keywords.append(kw_clean)

        log.info(f"Parsed keywords: {new_keywords}")

        if not new_keywords:
            await message.answer("❌ Не удалось распознать ключевые слова. Попробуйте еще раз.\n\n"
                                 "Отправьте слова через запятую, например: пвх, влагостойкие, 3д")
            return

        # Добавляем новые ключевые слова к существующим
        current_keywords = filter_data['keywords']
        added_count = 0

        for kw in new_keywords:
            if kw not in current_keywords:
                current_keywords.append(kw)
                added_count += 1
                log.info(f"Added keyword: {kw}")

        # Обновляем данные в памяти
        filter_data['keywords'] = current_keywords
        self.filter_sessions[session_id] = filter_data

        log.info(f"Added {added_count} new keywords, total now: {len(current_keywords)}")
        log.info(LogCodes.FLT_ADD_KEYWORDS, count=added_count)

        # Очищаем состояние
        await state.clear()
        log.info("FSM state cleared")

        # Удаляем сообщение с вводом ключевых слов (то, которое отправил пользователь)
        try:
            await message.delete()
            log.info("User input message deleted")
        except Exception as e:
            log.warning(f"Could not delete user message: {e}")

        # Отправляем краткое подтверждение (всплывающее уведомление, не новое сообщение)
        if added_count > 0:
            # Используем callback answer для быстрого уведомления
            # Но у нас нет callback, поэтому отправляем небольшое сообщение, которое само удалится
            confirm_msg = await message.answer(
                f"✅ Добавлено {added_count} слов. Всего: {len(current_keywords)}",
                show_alert=False
            )
            # Удаляем сообщение-подтверждение через 2 секунды
            import asyncio
            asyncio.create_task(self._delete_message_after_delay(confirm_msg, 2))

        # Находим и обновляем исходное сообщение с интерфейсом фильтрации
        try:
            # Пытаемся получить сообщение по chat_id и message_id
            if filter_message_id:
                # Получаем исходное сообщение (оно должно быть в том же чате)
                original_message = await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=filter_message_id,
                    text="🔄 Обновление...",
                    reply_markup=None
                )
                # Теперь обновляем его с интерфейсом фильтрации
                await self.show_filter_interface(original_message, session_id)
                log.info(f"Filter interface updated via stored message_id: {filter_message_id}")
            else:
                # Если нет сохраненного ID, пробуем через reply_to_message
                log.warning("No filter_message_id in state, trying alternative")
                await self.show_filter_interface(message, session_id)
        except Exception as e:
            log.error(f"Error updating filter interface: {e}")
            # Если не удалось обновить существующее сообщение, создаем новое
            new_msg = await message.answer("🔄 Возвращаюсь к фильтрации...")
            await self.show_filter_interface(new_msg, session_id)
            # Сохраняем новый ID
            self.filter_messages[session_id] = new_msg.message_id

    async def _delete_message_after_delay(self, message: Message, delay: int):
        """Удалить сообщение через задержку"""
        import asyncio
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except Exception:
            pass

    async def back_to_filter(self, callback: CallbackQuery, state: FSMContext):
        """Вернуться к интерфейсу фильтрации (отмена добавления)"""
        session_id = callback.data.replace("mf_back_", "")
        log.info(f"Back to filter for session: {session_id}")

        # Очищаем состояние
        await state.clear()

        # Возвращаемся к фильтрации
        await self.show_filter_interface(callback.message, session_id)
        await callback.answer()

    async def toggle_keyword(self, callback: CallbackQuery):
        """Изменить статус ключевого слова"""
        data = callback.data.replace("mf_toggle_", "")
        session_id, index_str = data.rsplit("_", 1)
        index = int(index_str)

        filter_data = self.filter_sessions.get(session_id)

        if not filter_data:
            await callback.answer("❌ Сессия фильтрации не найдена")
            return

        excluded = filter_data['excluded']

        if index in excluded:
            excluded.remove(index)
        else:
            excluded.append(index)

        filter_data['excluded'] = excluded
        self.filter_sessions[session_id] = filter_data

        await self.show_filter_interface(callback.message, session_id)
        await callback.answer()

    async def finish_manual_filter(self, callback: CallbackQuery, state: FSMContext):
        """Завершить фильтрацию и сохранить результат"""
        log.info(LogCodes.FLT_COMPLETE, total=0, filtered=0)

        await state.clear()

        user_id = callback.from_user.id
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            log.warning(LogCodes.ERR_SESSION_NOT_FOUND, id="unknown")
            await callback.answer("❌ Сессия не найдена")
            return

        filter_data = self.filter_sessions.get(session.id)

        if not filter_data:
            await callback.answer("❌ Сессия фильтрации не найдена")
            return

        all_keywords = filter_data['keywords']
        excluded = filter_data['excluded']

        filtered_keywords = [
            kw for i, kw in enumerate(all_keywords)
            if i not in excluded
        ]

        log.info(LogCodes.FLT_COMPLETE, total=len(all_keywords), filtered=len(filtered_keywords))

        session.keywords = filtered_keywords
        session.current_step = "keywords_filtered"

        session_repo.update(
            session.id,
            keywords=filtered_keywords,
            current_step="keywords_filtered"
        )

        # Очищаем временные данные
        if session.id in self.filter_sessions:
            del self.filter_sessions[session.id]
        if session.id in self.filter_messages:
            del self.filter_messages[session.id]

        category_name = "Неизвестно"
        if 'category_repo' in self.repositories:
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)
            if category:
                category_name = category.name

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
            text="✏️ Продолжить фильтрацию",
            callback_data=f"manual_filter_{session.id}"
        )
        builder.adjust(1)

        keywords_list = "\n".join([f"• {kw}" for kw in filtered_keywords[:20]])

        await callback.message.edit_text(
            f"✅ <b>Фильтрация завершена!</b>\n\n"
            f"📁 <b>Категория:</b> {category_name}\n"
            f"🎯 <b>Назначения:</b> {purposes_text}\n"
            f"📝 <b>Доп. параметры:</b> {additional_params_text}\n\n"
            f"📊 <b>Результат фильтрации:</b>\n"
            f"• Всего ключей: {len(filtered_keywords)}\n"
            f"• Исключено: {len(all_keywords) - len(filtered_keywords)}\n\n"
            f"<b>Ключевые слова:</b>\n{keywords_list}",
            reply_markup=builder.as_markup()
        )
        await callback.answer(f"✅ Оставлено {len(filtered_keywords)} ключевых слов")

    async def cancel_manual_filter(self, callback: CallbackQuery, state: FSMContext):
        """Отмена фильтрации"""
        session_id = callback.data.replace("mf_cancel_", "")
        log.info(LogCodes.FLT_CANCEL)

        await state.clear()

        if session_id in self.filter_sessions:
            del self.filter_sessions[session_id]
        if session_id in self.filter_messages:
            del self.filter_messages[session_id]

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if session:
            category_name = "Неизвестно"
            if 'category_repo' in self.repositories:
                category_repo = self.repositories['category_repo']
                category = category_repo.get_by_id(session.category_id)
                if category:
                    category_name = category.name

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

            keywords_preview = "\n".join([f"• {kw}" for kw in session.keywords[:15]])
            if len(session.keywords) > 15:
                keywords_preview += f"\n• ... и ещё {len(session.keywords) - 15}"

            builder = InlineKeyboardBuilder()
            builder.button(
                text="🎯 Меню генерации",
                callback_data=f"show_generation_menu_{session_id}"
            )
            builder.button(
                text="🔍 Собрать данные заново",
                callback_data=f"collect_data_{session_id}"
            )
            builder.adjust(1)

            await callback.message.edit_text(
                f"❌ <b>Фильтрация отменена</b>\n\n"
                f"📁 <b>Категория:</b> {category_name}\n"
                f"🎯 <b>Назначения:</b> {purposes_text}\n"
                f"📝 <b>Доп. параметры:</b> {additional_params_text}\n\n"
                f"<b>Ключевые слова:</b>\n{keywords_preview}",
                reply_markup=builder.as_markup()
            )
        else:
            builder = InlineKeyboardBuilder()
            builder.button(
                text="🎯 Меню генерации",
                callback_data=f"show_generation_menu_{session_id}"
            )
            builder.button(
                text="🔍 Собрать данные заново",
                callback_data=f"collect_data_{session_id}"
            )
            builder.adjust(1)

            await callback.message.edit_text(
                "❌ <b>Фильтрация отменена</b>\n\n"
                "Ключевые слова остались без изменений.",
                reply_markup=builder.as_markup()
            )

        await callback.answer()