# app/bot/handlers/category_handler.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.bot.handlers.base_handler import BaseMessageHandler
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class CategoryHandler(BaseMessageHandler):
    """Обработчик выбора категории и назначения"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()
        self.scraper_service = services.get('scraper')
        self.categories = {}

    async def register(self, dp):
        """Регистрация обработчиков"""
        if not self.scraper_service:
            log.error(LogCodes.ERR_MPSTATS, error="Scraper service not found")
            from app.services.mpstats_scraper_service import MPStatsScraperService
            self.scraper_service = MPStatsScraperService(self.config)
            await self.scraper_service.initialize_scraper()

        dp.include_router(self.router)
        self.router.message.register(self.reset_session, Command(commands=["reset"]))
        self.router.message.register(self.handle_additional_params, F.text & ~F.text.startswith('/'))
        self.router.callback_query.register(self.handle_category_select, F.data.startswith("category_"))
        self.router.callback_query.register(self.handle_purpose_select, F.data.startswith("purpose_"))
        self.router.callback_query.register(self.handle_purpose_done, F.data.startswith("purpose_done_"))
        self.router.callback_query.register(self.handle_back_to_categories, F.data == "back_to_categories")
        self.router.callback_query.register(self.handle_back_to_main_menu, F.data == "back_to_main_menu")
        self.router.callback_query.register(self.handle_skip_additional_params, F.data == "skip_additional_params")

    async def show_categories_command(self, message: Message):
        """Обработка команды /categories"""
        await self.show_categories(message)

    def _get_category_name(self, category_id: str) -> str:
        """Получить название категории по ID"""
        if 'category_repo' in self.repositories:
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(category_id)
            if category:
                return category.name

        # Запасные варианты
        categories_data = {
            "123":'123',
            "electronics": "📱 Электроника",
            "clothing": "👕 Одежда и обувь",
            "home": "🏠 Дом и сад",
            "beauty": "💄 Красота и здоровье"
        }

        return categories_data.get(category_id, "Неизвестная категория")


    async def handle_back_to_categories(self, callback: CallbackQuery):
        """Возврат к выбору категорий"""
        await callback.answer()

        user_id = callback.from_user.id
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        # Загружаем категории если нужно
        if not self.categories:
            await self.load_categories_from_db()

        # Создаем новую клавиатуру
        builder = InlineKeyboardBuilder()
        for category_id, category_data in self.categories.items():
            builder.button(
                text=category_data["name"],
                callback_data=f"category_{category_id}"
            )

        builder.button(text="↩️ Назад в меню", callback_data="back_to_main_menu")
        builder.adjust(1)

        # Формируем текст с текущими параметрами
        welcome_text = "📁 <b>Выберите категорию товара:</b>"

        if session:
            if session.category_id:
                category_name = self._get_category_name(session.category_id)
                welcome_text = f"📁 <b>Выберите категорию товара:</b>\n\n" \
                               f"✅ <b>Текущая категория:</b> {category_name}"

                if session.purposes:
                    # Получаем назначения как строку
                    purposes_text = ""
                    if isinstance(session.purposes, list):
                        purposes_text = ", ".join(session.purposes)
                    else:
                        purposes_text = str(session.purposes)
                    welcome_text += f"\n✅ <b>Назначения:</b> {purposes_text}"  # ИЗМЕНЕНО

                if session.additional_params:
                    welcome_text += f"\n✅ <b>Доп. параметры:</b> {', '.join(session.additional_params)}"

        # Редактируем существующее сообщение
        await callback.message.edit_text(
            welcome_text,
            reply_markup=builder.as_markup()
        )




    async def load_categories_from_db(self):
        """Загрузка категорий из базы данных"""
        try:
            category_repo = self.repositories.get('category_repo')
            if not category_repo:
                log.error(LogCodes.ERR_DATABASE, error="Category repository not found")
                return

            categories = category_repo.get_all()

            if not categories:
                log.warning(LogCodes.DB_RECORD_NOT_FOUND, table="categories", id="all")
                return

            self.categories = {}
            for category in categories:
                purposes_dict = {}
                if category.purposes and isinstance(category.purposes, dict):
                    purposes_dict = category.purposes

                self.categories[category.id] = {
                    "name": category.name,
                    "description": category.description or "",
                    "purposes": purposes_dict
                }

            log.info(LogCodes.DB_RECORD_FOUND, table="categories", id=f"{len(self.categories)} records")

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=str(e))




    # async def handle_go_to_generate(self, callback: CallbackQuery):
    #     """Перейти к генерации"""
    #     user_id = callback.from_user.id
    #     await callback.answer("✅ Способ генерации сохранен")
    #     await callback.message.answer("Теперь используйте команду /generate для создания контента")



    def _get_purposes_names(self, category_id: str, purpose_ids: list) -> list:
        """Получить названия назначений по их ID"""
        if not self.categories:
            return purpose_ids  # Если категории не загружены, возвращаем ID

        category_data = self.categories.get(category_id)
        if not category_data or not category_data.get("purposes"):
            return purpose_ids

        purposes_dict = category_data["purposes"]
        names = []

        for purpose_id in purpose_ids:
            name = purposes_dict.get(purpose_id, purpose_id)
            names.append(name)

        return names



    async def show_categories_command(self, message: Message):
        """Обработка команды /categories"""
        await self.show_categories(message)

    async def show_categories(self, message: Message, from_back: bool = False):
        """Показать список категорий"""
        user_id = message.from_user.id

        # Загружаем категории из базы, если еще не загружены
        if not self.categories:
            await self.load_categories_from_db()

        if not self.categories:
            await message.answer(
                "❌ <b>Категории не найдены!</b>\n\n"
                "Пожалуйста, сообщите администратору для настройки категорий."
            )
            return

        # Создаем клавиатуру с категориями
        builder = InlineKeyboardBuilder()
        for category_id, category_data in self.categories.items():
            builder.button(
                text=category_data["name"],
                callback_data=f"category_{category_id}"
            )

        builder.button(text="↩️ Назад в меню", callback_data="back_to_main_menu")
        builder.adjust(1)

        welcome_text = "📁 <b>Выберите категорию товара:</b>"

        # Если у пользователя есть активная сессия, показываем выбранные параметры
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if session and session.category_id:
            category_name = self._get_category_name(session.category_id)
            welcome_text = f"📁 <b>Выберите категорию товара:</b>\n\n" \
                           f"✅ <b>Текущая категория:</b> {category_name}"

            if session.purpose:
                welcome_text += f"\n✅ <b>Назначения:</b> {self._get_purposes_display_text(session)}"

            if session.additional_params:
                welcome_text += f"\n✅ <b>Доп. параметры:</b> {', '.join(session.additional_params)}"

        await message.answer(
            welcome_text,
            reply_markup=builder.as_markup()
        )

    async def handle_category_select(self, callback: CallbackQuery):
        """Обработка выбора категории"""
        user_id = str(callback.from_user.id)
        category_id = callback.data.replace("category_", "")

        if not self.categories:
            await self.load_categories_from_db()

        category_data = self.categories.get(category_id)
        if not category_data:
            log.warning(LogCodes.ERR_CATEGORY_NOT_FOUND, id=category_id)
            await callback.answer(f"❌ Категория не найдена")
            return

        session_repo = self.repositories['session_repo']
        try:
            existing_session = session_repo.get_active_session(user_id)

            if existing_session:
                existing_session.category_id = category_id
                existing_session.purposes = []
                session_repo.update(
                    existing_session.id,
                    category_id=category_id,
                    purposes=[],
                    current_step="category_selected"
                )
                session = existing_session
                log.info(LogCodes.DB_RECORD_UPDATED, table="user_session", id=session.id)
            else:
                session = session_repo.create_new_session(
                    user_id=user_id,
                    category_id=category_id,
                    purposes=[],
                    current_step="category_selected"
                )
                log.info(LogCodes.DB_SESSION_CREATED, id=session.id)

            log.info(LogCodes.USR_SELECT_CATEGORY, category=category_data['name'])
            await self._show_purposes_selection(callback.message, category_id, category_data, [])
            await callback.answer(f"Выбрана категория: {category_data['name']}")

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=str(e))
            await callback.message.edit_text(
                "❌ <b>Ошибка при создании сессии</b>\nПопробуйте еще раз."
            )
            await callback.answer()

    async def handle_purpose_select(self, callback: CallbackQuery):
        """Обработка выбора/отмены назначения (множественный выбор)"""
        user_id = callback.from_user.id

        # Проверяем кнопку "Готово"
        if callback.data.startswith("purpose_done_"):
            await self.handle_purpose_done(callback)
            return

        data = callback.data.replace("purpose_", "")

        # Парсим callback_data
        action = "select"
        for act in ['select', 'remove']:
            if data.endswith(f"_{act}"):
                action = act
                data = data.replace(f"_{act}", "")
                break

        # Находим category_id и purpose_id
        category_id = None
        purpose_id = None

        for cat_id in self.categories.keys():
            if data.startswith(f"{cat_id}_"):
                category_id = cat_id
                purpose_id = data.replace(f"{cat_id}_", "")
                break

        if not category_id or not purpose_id:
            log.warning(LogCodes.ERR_PARSE, data=callback.data)
            await callback.answer("❌ Ошибка разбора данных")
            return

        category_data = self.categories.get(category_id)
        if not category_data:
            await callback.answer(f"❌ Категория не найдена")
            return

        purpose_name = category_data["purposes"].get(purpose_id)
        if not purpose_name:
            await callback.answer(f"❌ Назначение не найдено")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            # Создаем сессию
            user_repo = self.repositories['user_repo']
            user = user_repo.get_or_create(
                telegram_id=user_id,
                username=callback.from_user.username,
                first_name=callback.from_user.first_name,
                last_name=callback.from_user.last_name
            )
            session = session_repo.create_new_session(
                user_id=user_id,
                category_id=category_id,
                purposes=[],
                current_step="category_selected"
            )

        if session.category_id != category_id:
            session.category_id = category_id

        if not session.purposes:
            session.purposes = []

        current_purposes = session.purposes.copy()

        if action == "select":
            if purpose_id not in current_purposes:
                current_purposes.append(purpose_id)
        elif action == "remove":
            if purpose_id in current_purposes:
                current_purposes.remove(purpose_id)

        session.purposes = current_purposes
        session.current_step = "purposes_selecting" if current_purposes else "category_selected"

        session_repo.update(
            session.id,
            category_id=category_id,
            purposes=current_purposes,
            current_step=session.current_step
        )

        await self._show_purposes_selection(callback.message, category_id, category_data, current_purposes)
        await callback.answer()

    async def _show_purposes_selection(self, message: Message, category_id: str, category_data: dict,
                                       selected_purposes_ids: list):
        """Показать интерфейс выбора назначений с кнопкой завершения"""
        builder = InlineKeyboardBuilder()


        # Показываем все доступные назначения
        for purpose_id, purpose_name in category_data["purposes"].items():
            # Проверяем, выбрано ли уже это назначение
            is_selected = purpose_id in selected_purposes_ids
            action = "remove" if is_selected else "select"
            icon = "✅" if is_selected else "⬜"

            # ИСПРАВЛЕНО: Не заменяем подчеркивания!
            callback_data = f"purpose_{category_id}_{purpose_id}_{action}"



            builder.button(
                text=f"{icon} {purpose_name}",
                callback_data=callback_data
            )

        # Кнопка "Готово"
        if selected_purposes_ids:
            builder.button(
                text=f"✅ ГОТОВО ({len(selected_purposes_ids)} выбрано)",
                callback_data=f"purpose_done_{category_id}"  # Без замены подчеркиваний!
            )

        # Кнопка "Назад"
        builder.button(text="↩️ Назад к категориям", callback_data="back_to_categories")
        builder.adjust(1)

        # Формируем текст с ЯСНЫМ указанием многократного выбора
        category_name = category_data["name"]
        text = f"✅ <b>Выбрана категория:</b> {category_name}\n\n"
        text += f"📝 {category_data['description']}\n\n"

        if selected_purposes_ids:
            text += f"🎯 <b>Выбрано назначений:</b> {len(selected_purposes_ids)}\n"
            # Показываем названия
            selected_names = []
            for purpose_id in selected_purposes_ids:
                purpose_name = category_data["purposes"].get(purpose_id, purpose_id)
                selected_names.append(purpose_name)
            text += "• " + "\n• ".join(selected_names) + "\n\n"

        text += "🎯 <b>Выберите одно или несколько назначений:</b>\n"
        text += "<i>Нажмите на назначение чтобы выбрать/отменить</i>\n"
        text += "<i>Кнопки с ✅ уже выбраны</i>"

        if hasattr(message, 'edit_text'):
            await message.edit_text(
                text,
                reply_markup=builder.as_markup()
            )
        else:
            await message.answer(
                text,
                reply_markup=builder.as_markup()
            )

    async def handle_purpose_done(self, callback: CallbackQuery):
        """Завершение выбора назначений"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            log.warning(LogCodes.ERR_SESSION_NOT_FOUND, id="unknown")
            await callback.answer("❌ Сессия не найдена")
            return

        if not session.purposes:
            await callback.answer("❌ Выберите хотя бы одно назначение")
            return

        session.current_step = "purposes_selected"
        session_repo.update(session.id, current_step="purposes_selected")

        log.info(LogCodes.USR_COMPLETE_SETUP)
        await self.show_additional_params_request(callback.message, session)
        await callback.answer("✅ Выбор завершен")

    # В category_handler.py изменим метод handle_back_to_main_menu:
    async def handle_back_to_main_menu(self, callback: CallbackQuery):
        """Возврат в главное меню без сброса сессии"""
        await callback.answer()



        await callback.message.answer(
            "🏠 <b>Главное меню</b>\n\n"
            "🤖 <b>Добро пожаловать в генератор контента для маркетплейсов!</b>\n\n"
            "Я помогу вам создать оптимизированный контент для ваших товаров.\n\n"
            "<b>Доступные команды:</b>\n"
            "/categories - Выбрать категорию и назначение товара\n"
            "/generate - Сгенерировать контент\n"
            "/reset - Сбросить текущую сессию\n"
            "/about - О боте\n"
            "/help - Помощь\n\n"
            "<i>Вы можете продолжить с того места, где остановились.</i>"
        )

    async def show_additional_params_request(self, message: Message, session, from_back: bool = False):
        """Показать запрос дополнительных параметров с кнопками"""
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Не указывать доп. параметры", callback_data="skip_additional_params")
        builder.button(text="↩️ Назад к назначению", callback_data="back_to_purpose")
        builder.adjust(1)

        welcome_text = (
            "📋 <b>Хотите добавить дополнительные параметры?</b>\n\n"
            "<i>Например: 'высокая производительность, AMOLED дисплей, долгая батарея'</i>\n\n"
            "📝 <b>Отправьте параметры через запятую:</b>"
        )

        if from_back:
            welcome_text = (
                "📋 <b>Добавьте дополнительные параметры:</b>\n\n"
                "<i>Или нажмите 'Не указывать доп. параметры'</i>\n\n"
                "📝 <b>Отправьте параметры через запятую:</b>"
            )

        await message.answer(
            welcome_text,
            reply_markup=builder.as_markup()
        )

    async def handle_skip_additional_params(self, callback: CallbackQuery):
        """Пропуск дополнительных параметров - сразу сбор данных"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        session.additional_params = []
        session.current_step = "ready_for_data_collection"

        session_repo.update(
            session.id,
            additional_params=[],
            current_step="ready_for_data_collection"
        )

        # Сразу показываем кнопку сбора данных
        await self._show_data_collection_button(callback.message, session)
        await callback.answer()

    async def handle_additional_params(self, message: Message, state: FSMContext = None):
        """Обработка ввода дополнительных параметров"""
        user_id = message.from_user.id

        if state:
            current_state = await state.get_state()
            if current_state == "FilterStates:waiting_for_keywords":
                return

        if message.text and message.text.startswith('/'):
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            return

        if session.current_step == "purposes_selected":
            await self._handle_initial_params_input(message, session)
            return

        if getattr(session, 'is_changing_params', False):
            await self._handle_update_params_input(message, session)
            return

    async def _handle_initial_params_input(self, message: Message, session):
        """Обработка первоначального ввода параметров"""
        params_text = message.text.strip().lower()
        additional_params = []

        if params_text != "нет":
            additional_params = [param.strip() for param in params_text.split(',') if param.strip()]

        session.additional_params = additional_params
        session.current_step = "ready_for_data_collection"

        session_repo = self.repositories['session_repo']
        session_repo.update(
            session.id,
            additional_params=additional_params,
            current_step="ready_for_data_collection"
        )

        if additional_params:
            log.info(LogCodes.USR_ADD_PARAMS, count=len(additional_params))

        await self._show_data_collection_button(message, session)

    async def _show_data_collection_button(self, message: Message, session):
        """Показать кнопку сбора данных после ввода параметров"""
        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()

        builder.button(text="🔍 Собрать данные с MPStats", callback_data=f"collect_data_{session.id}")
        builder.button(text="📝 Изменить параметры", callback_data="back_to_purpose")
        builder.button(text="🏠 Главное меню", callback_data="back_to_main_menu")
        builder.adjust(1)

        # Получаем информацию о категории и назначениях
        category_name = self._get_category_name(session.category_id)
        purpose_names = self._get_purposes_names(session.category_id, session.purposes or [])
        purposes_text = ", ".join(purpose_names) if purpose_names else "не указано"

        success_message = "✅ <b>Параметры сохранены!</b>\n\n"
        success_message += f"📋 <b>Параметры товара:</b>\n"
        success_message += f"• <b>Категория:</b> {category_name}\n"
        success_message += f"• <b>Назначения:</b> {purposes_text}\n"

        if session.additional_params:
            success_message += f"• <b>Доп. параметры:</b> {', '.join(session.additional_params)}\n\n"
        else:
            success_message += f"• <b>Доп. параметры:</b> не указаны\n\n"

        success_message += "🔍 <b>Следующий шаг:</b>\n"
        success_message += "• Сбор ключевых слов с MPStats\n"
        success_message += "• Фильтрация через GPT\n"
        success_message += "• Подготовка к генерации контента\n\n"
        success_message += "Нажмите кнопку ниже чтобы начать сбор данных:"

        await message.answer(
            success_message,
            reply_markup=builder.as_markup()
        )

    def _get_purposes_display_text(self, session) -> str:
        """Получить назначения в виде читаемого текста"""
        if not session.purposes:
            return "не указаны"

        if not isinstance(session.purposes, list):
            return str(session.purposes)

        if len(session.purposes) == 0:
            return "не указаны"

        # Переводим ID в названия
        purpose_names = []
        if self.categories and session.category_id in self.categories:
            category_data = self.categories[session.category_id]
            if "purposes" in category_data:
                purposes_dict = category_data["purposes"]  # Здесь ключи английские, значения русские
                for purpose_id in session.purposes:
                    purpose_name = purposes_dict.get(purpose_id, purpose_id)
                    purpose_names.append(purpose_name)

        if not purpose_names:
            purpose_names = [str(p) for p in session.purposes]

        return ", ".join(purpose_names)


    async def _handle_update_params_input(self, message: Message, session):
        """Обработка обновления параметров после генерации"""
        session_repo = self.repositories['session_repo']

        params_text = message.text.strip()

        # Проверяем отмену
        if params_text.lower() == "отмена":
            session.is_changing_params = False
            session_repo.update(session.id, is_changing_params=False)

            await message.answer("❌ Изменение параметров отменено")
            return

        additional_params = []

        if params_text.lower() != "нет":
            # Разбиваем параметры по запятой
            additional_params = [param.strip() for param in params_text.split(',') if param.strip()]

        # Обновляем параметры в сессии
        session.additional_params = additional_params
        session.is_changing_params = False
        session_repo.update(
            session.id,
            additional_params=additional_params,
            is_changing_params=False
        )

        # Получаем название категории для сообщения
        category_name = self._get_category_name(session.category_id)

        # Показываем обновленные параметры
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Сгенерировать с новыми параметрами", callback_data="generate_title")
        builder.button(text="📝 Изменить еще раз", callback_data="change_additional_params")
        builder.button(text="↩️ Назад к параметрам", callback_data="change_params")
        builder.adjust(1)



        await message.answer(
            f"✅ <b>Параметры товара обновлены:</b>\n\n"
            f"📁 <b>Категория:</b> {category_name}\n"
            f"🎯 <b>Назначение:</b> {self._get_purposes_display_text(session)}\n"
            f"📝 <b>Доп. параметры:</b> {', '.join(additional_params) if additional_params else 'нет'}\n\n"
            "Что делаем дальше?",
            reply_markup=builder.as_markup()
        )

    async def reset_session(self, message: Message, state: FSMContext = None):
        """Сброс сессии"""
        user_id = message.from_user.id

        if state:
            await state.clear()

        session_repo = self.repositories['session_repo']
        active_sessions = session_repo.get_active_session(user_id)
        if active_sessions:
            if isinstance(active_sessions, list):
                for session in active_sessions:
                    session_repo.update(session.id, is_active=False)
            else:
                session_repo.update(active_sessions.id, is_active=False)

        log.info(LogCodes.USR_RESET_SESSION)
        await message.answer(
            "🔄 <b>Сессия сброшена</b>\n"
            "Начните заново с <code>/start</code>"
        )