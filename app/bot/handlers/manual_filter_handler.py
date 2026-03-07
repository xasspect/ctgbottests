# app/bot/handlers/manual_filter_handler.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.bot.handlers.base_handler import BaseMessageHandler


class FilterStates(StatesGroup):
    """Состояния для FSM"""
    waiting_for_keywords = State()  # Ожидание ввода ключевых слов


class ManualFilterHandler(BaseMessageHandler):
    """Обработчик ручной фильтрации ключевых слов (данные в памяти)"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()
        self.logger = logging.getLogger(__name__)
        # Хранилище временных данных фильтрации в памяти
        # Структура: {session_id: {'keywords': [], 'excluded': []}}
        self.filter_sessions = {}

    async def register(self, dp):
        """Регистрация обработчиков"""
        dp.include_router(self.router)

        self.logger.info("Registering ManualFilterHandler callbacks")

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

        # Кнопки для добавления ключевых слов
        self.router.callback_query.register(
            self.show_add_keywords_menu,
            F.data.startswith("mf_add_menu_")
        )
        self.router.callback_query.register(
            self.start_add_keywords,
            F.data.startswith("mf_add_start_")
        )
        self.router.callback_query.register(
            self.back_to_filter,
            F.data.startswith("mf_back_")
        )

        # ИСПРАВЛЕНИЕ: Регистрируем обработчик сообщений с правильным фильтром
        # Используем FilterStates.waiting_for_keywords как фильтр состояния
        self.router.message.register(
            self.process_added_keywords,
            FilterStates.waiting_for_keywords  # Только когда в этом состоянии
        )

        self.logger.info("ManualFilterHandler callbacks registered")

    async def start_manual_filter(self, callback: CallbackQuery, state: FSMContext):
        """Начать ручную фильтрацию ключевых слов"""
        self.logger.info(f"=== start_manual_filter called with data: {callback.data} ===")

        # Очищаем состояние перед началом
        await state.clear()

        session_id = callback.data.replace("manual_filter_", "")
        self.logger.info(f"Extracted session_id: {session_id}")

        # Получаем сессию из репозитория
        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            self.logger.warning(f"Session not found: {session_id}")
            await callback.answer("❌ Сессия не найдена")
            return

        if not session.keywords:
            self.logger.warning(f"No keywords in session: {session_id}")
            # Если нет ключевых слов, создаем пустой список
            session.keywords = []
            session_repo.update(session.id, keywords=[])

        self.logger.info(f"Session found with {len(session.keywords)} keywords")

        # Сохраняем данные фильтрации в памяти
        self.filter_sessions[session_id] = {
            'keywords': session.keywords.copy(),  # копия для фильтрации
            'excluded': []  # индексы исключенных слов
        }

        self.logger.info(f"Filter session created with {len(session.keywords)} keywords")

        await self.show_filter_interface(callback.message, session_id)
        await callback.answer()

    async def show_filter_interface(self, message: Message, session_id: str):
        """Показать интерфейс фильтрации"""
        # Получаем данные фильтрации из памяти
        filter_data = self.filter_sessions.get(session_id)

        if not filter_data:
            self.logger.warning(f"Filter session not found: {session_id}")
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
        builder.button(text="➕ Добавить ключевые слова", callback_data=f"mf_add_menu_{session_id}")
        builder.button(text="✅ Завершить", callback_data="mf_done")
        builder.button(text="❌ Отмена", callback_data=f"mf_cancel_{session_id}")
        builder.adjust(1)

        selected_count = len(keywords) - len(excluded)

        # Формируем текст со списком всех ключевых слов
        keywords_text = ""
        if keywords:
            keywords_list = []
            for i, kw in enumerate(keywords):
                status_icon = "✅" if i not in excluded else "❌"
                keywords_list.append(f"{status_icon} {kw}")
            keywords_text = "\n".join(keywords_list[:20])  # Показываем первые 20
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

    async def toggle_keyword(self, callback: CallbackQuery):
        """Изменить статус ключевого слова"""
        # Парсим callback_data: mf_toggle_{session_id}_{index}
        data = callback.data.replace("mf_toggle_", "")
        session_id, index_str = data.rsplit("_", 1)
        index = int(index_str)

        self.logger.info(f"Toggling keyword {index} for session {session_id}")

        # Получаем данные фильтрации из памяти
        filter_data = self.filter_sessions.get(session_id)

        if not filter_data:
            self.logger.warning(f"Filter session not found: {session_id}")
            await callback.answer("❌ Сессия фильтрации не найдена")
            return

        excluded = filter_data['excluded']

        # Переключаем статус
        if index in excluded:
            excluded.remove(index)
            self.logger.info(f"Keyword {index} included")
        else:
            excluded.append(index)
            self.logger.info(f"Keyword {index} excluded")

        # Обновляем данные в памяти
        filter_data['excluded'] = excluded
        self.filter_sessions[session_id] = filter_data

        # Обновляем интерфейс
        await self.show_filter_interface(callback.message, session_id)
        await callback.answer()

    async def show_add_keywords_menu(self, callback: CallbackQuery):
        """Показать меню добавления ключевых слов"""
        session_id = callback.data.replace("mf_add_menu_", "")

        builder = InlineKeyboardBuilder()
        builder.button(
            text="✏️ Ввести ключевые слова",
            callback_data=f"mf_add_start_{session_id}"
        )
        builder.button(
            text="↩️ Назад к фильтрации",
            callback_data=f"mf_back_{session_id}"
        )
        builder.adjust(1)

        await callback.message.edit_text(
            f"📝 <b>Добавление ключевых слов</b>\n\n"
            f"Введите новые ключевые слова через запятую.\n\n"
            f"<i>Например: пвх, влагостойкие, 3д, белые</i>\n\n"
            f"Или нажмите кнопку ниже для ввода:",
            reply_markup=builder.as_markup()
        )
        await callback.answer()

    async def start_add_keywords(self, callback: CallbackQuery, state: FSMContext):
        """Начать процесс добавления ключевых слов"""
        session_id = callback.data.replace("mf_add_start_", "")

        self.logger.info(f"=== start_add_keywords called for session {session_id} ===")
        self.logger.info(f"User ID: {callback.from_user.id}")

        # Очищаем предыдущее состояние
        await state.clear()

        # Сохраняем session_id в состоянии
        await state.update_data(filter_session_id=session_id)
        await state.set_state(FilterStates.waiting_for_keywords)

        # Проверяем, что состояние установилось
        current_state = await state.get_state()
        current_data = await state.get_data()

        self.logger.info(f"State set to: {current_state}")
        self.logger.info(f"State data after set: {current_data}")

        builder = InlineKeyboardBuilder()
        builder.button(
            text="↩️ Отмена",
            callback_data=f"mf_back_{session_id}"
        )
        builder.adjust(1)

        await callback.message.edit_text(
            f"✏️ <b>Введите ключевые слова</b>\n\n"
            f"Отправьте список ключевых слов через запятую.\n\n"
            f"<i>Например: пвх, влагостойкие, 3д, белые, под камень</i>",
            reply_markup=builder.as_markup()
        )
        await callback.answer()

    async def process_added_keywords(self, message: Message, state: FSMContext):
        """Обработать введенные ключевые слова"""
        self.logger.info(f"=== process_added_keywords START ===")
        self.logger.info(f"Message text: {message.text}")
        self.logger.info(f"Message from user: {message.from_user.id}")

        # Проверяем текущее состояние
        current_state = await state.get_state()
        self.logger.info(f"Current state from FSM: {current_state}")

        # Получаем все данные из состояния для отладки
        state_data = await state.get_data()
        self.logger.info(f"State data: {state_data}")

        if current_state != FilterStates.waiting_for_keywords:
            self.logger.warning(f"Wrong state: {current_state}, expected: {FilterStates.waiting_for_keywords}")
            return

        # Получаем данные из состояния
        session_id = state_data.get('filter_session_id')
        self.logger.info(f"Session ID from state: {session_id}")

        if not session_id:
            self.logger.warning("No session_id in state")
            await message.answer("❌ Сессия не найдена. Начните заново.")
            await state.clear()
            return

        # Получаем данные фильтрации из памяти
        filter_data = self.filter_sessions.get(session_id)
        self.logger.info(f"Filter data from memory: {filter_data is not None}")

        if not filter_data:
            self.logger.warning(f"Filter session not found: {session_id}")
            await message.answer("❌ Сессия фильтрации не найдена")
            await state.clear()
            return

        # Парсим введенные ключевые слова
        input_text = message.text.strip()
        self.logger.info(f"Input text: {input_text}")

        # Разделяем по запятой и очищаем
        new_keywords = []
        for kw in input_text.split(','):
            kw_clean = kw.strip().lower()
            if kw_clean and kw_clean not in new_keywords:
                new_keywords.append(kw_clean)

        self.logger.info(f"Parsed keywords: {new_keywords}")

        if not new_keywords:
            await message.answer("❌ Не удалось распознать ключевые слова. Попробуйте еще раз.")
            return

        # Добавляем новые ключевые слова к существующим
        current_keywords = filter_data['keywords']

        added_count = 0
        for kw in new_keywords:
            if kw not in current_keywords:
                current_keywords.append(kw)
                added_count += 1
                self.logger.info(f"Added keyword: {kw}")

        # Обновляем данные в памяти
        filter_data['keywords'] = current_keywords
        self.filter_sessions[session_id] = filter_data

        self.logger.info(f"Added {added_count} new keywords, total now: {len(current_keywords)}")

        # Очищаем состояние
        await state.clear()
        self.logger.info("State cleared")

        # Удаляем сообщение с вводом ключевых слов
        try:
            await message.delete()
            self.logger.info("Input message deleted")
        except Exception as e:
            self.logger.warning(f"Could not delete message: {e}")

        # ИСПРАВЛЕНИЕ: Получаем сообщение для обновления интерфейса фильтрации
        # Используем reply_to_message или отправляем новое сообщение
        if message.reply_to_message:
            await self.show_filter_interface(message.reply_to_message, session_id)
            self.logger.info("Filter interface updated via reply_to_message")
        else:
            # Если нет reply_to_message, отправляем новое сообщение
            await message.answer(
                f"✅ Добавлено {added_count} новых ключевых слов.\n"
                f"Всего ключевых слов: {len(current_keywords)}"
            )
            # И отправляем новое сообщение с интерфейсом фильтрации
            new_msg = await message.answer("Загружаю интерфейс фильтрации...")
            await self.show_filter_interface(new_msg, session_id)
            self.logger.info("New filter interface message sent")

        self.logger.info("=== process_added_keywords END ===")

    async def back_to_filter(self, callback: CallbackQuery, state: FSMContext):
        """Вернуться к интерфейсу фильтрации"""
        session_id = callback.data.replace("mf_back_", "")

        # Очищаем состояние
        await state.clear()

        # Возвращаемся к фильтрации
        await self.show_filter_interface(callback.message, session_id)
        await callback.answer()

    async def finish_manual_filter(self, callback: CallbackQuery, state: FSMContext):
        """Завершить фильтрацию и сохранить результат"""
        self.logger.info("=== finish_manual_filter called ===")

        # Очищаем состояние
        await state.clear()

        # Получаем активную сессию пользователя
        user_id = callback.from_user.id
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            self.logger.warning(f"No active session for user {user_id}")
            await callback.answer("❌ Сессия не найдена")
            return

        # Получаем данные фильтрации из памяти
        filter_data = self.filter_sessions.get(session.id)

        if not filter_data:
            self.logger.warning(f"Filter session not found: {session.id}")
            await callback.answer("❌ Сессия фильтрации не найдена")
            return

        # Применяем фильтр
        all_keywords = filter_data['keywords']
        excluded = filter_data['excluded']

        filtered_keywords = [
            kw for i, kw in enumerate(all_keywords)
            if i not in excluded
        ]

        self.logger.info(f"Filtered from {len(all_keywords)} to {len(filtered_keywords)} keywords")

        # Обновляем сессию в БД
        session.keywords = filtered_keywords
        session.current_step = "keywords_filtered"

        session_repo.update(
            session.id,
            keywords=filtered_keywords,
            current_step="keywords_filtered"
        )

        # Очищаем временные данные из памяти
        if session.id in self.filter_sessions:
            del self.filter_sessions[session.id]
            self.logger.info(f"Filter session {session.id} cleaned from memory")

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
                # Переводим ID назначений в русские названия
                purpose_map = {
                    "wood": "под дерево", "with_pattern": "с рисунком", "kitchen": "кухня",
                    "tile": "плитка", "3d": "3D", "in_roll": "в рулоне",
                    "self_adhesive": "самоклеящиеся", "stone": "под камень", "bathroom": "ванная",
                    "bedroom": "спальня", "brick": "под кирпич", "marble": "под мрамор",
                    "living_room": "гостиная", "white": "белый"
                }
                translated = []
                for p in session.purposes:
                    translated.append(purpose_map.get(str(p).lower(), str(p)))
                purposes_text = ", ".join(translated)
            else:
                purposes_text = str(session.purposes)

        # Дополнительные параметры
        additional_params_text = "не указаны"
        if session.additional_params:
            if isinstance(session.additional_params, list):
                additional_params_text = ", ".join(session.additional_params)
            else:
                additional_params_text = str(session.additional_params)

        # Формируем клавиатуру
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

        # Формируем полный список ключевых слов
        keywords_list = "\n".join([f"• {kw}" for kw in filtered_keywords])

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

        # Очищаем состояние
        await state.clear()

        self.logger.info(f"Cancelling filter session: {session_id}")

        # Очищаем временные данные из памяти
        if session_id in self.filter_sessions:
            del self.filter_sessions[session_id]
            self.logger.info(f"Filter session {session_id} cleaned from memory")

        # Получаем сессию для отображения данных
        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if session:
            # Получаем название категории
            category_name = "Неизвестно"
            if 'category_repo' in self.repositories:
                category_repo = self.repositories['category_repo']
                category = category_repo.get_by_id(session.category_id)
                if category:
                    category_name = category.name

            # Получаем назначения
            purposes_text = "не указаны"
            if hasattr(session, 'purposes') and session.purposes:
                if isinstance(session.purposes, list):
                    purpose_map = {
                        "wood": "под дерево", "with_pattern": "с рисунком", "kitchen": "кухня",
                        "tile": "плитка", "3d": "3D", "in_roll": "в рулоне",
                        "self_adhesive": "самоклеящиеся", "stone": "под камень", "bathroom": "ванная",
                        "bedroom": "спальня", "brick": "под кирпич", "marble": "под мрамор",
                        "living_room": "гостиная", "white": "белый"
                    }
                    translated = []
                    for p in session.purposes:
                        translated.append(purpose_map.get(str(p).lower(), str(p)))
                    purposes_text = ", ".join(translated)
                else:
                    purposes_text = str(session.purposes)

            # Дополнительные параметры
            additional_params_text = "не указаны"
            if session.additional_params:
                if isinstance(session.additional_params, list):
                    additional_params_text = ", ".join(session.additional_params)
                else:
                    additional_params_text = str(session.additional_params)

            # Ключевые слова
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
            # Если сессия не найдена, просто показываем сообщение об отмене
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