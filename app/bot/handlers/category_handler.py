# app/bot/handlers/category_handler.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder


class CategoryHandler(BaseMessageHandler):
    """Обработчик выбора категории и назначения"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()
        self.scraper_service = services.get('scraper')
        self.categories = {}  # Будем заполнять из базы данных

    async def register(self, dp):
        """Регистрация обработчиков"""
        if not self.scraper_service:
            self.logger.error("Scraper service not found!")
            # Можно создать его здесь, если нужно
            from app.services.mpstats_scraper_service import MPStatsScraperService
            self.scraper_service = MPStatsScraperService(self.config)
            await self.scraper_service.initialize_scraper()

        dp.include_router(self.router)
        self.router.message.register(self.show_categories_command, Command(commands=["categories"]))
        self.router.message.register(self.reset_session, Command(commands=["reset"]))
        self.router.message.register(self.handle_additional_params, F.text & ~F.command)
        self.router.callback_query.register(self.handle_category_select, F.data.startswith("category_"))
        self.router.callback_query.register(self.handle_purpose_select, F.data.startswith("purpose_"))
        self.router.callback_query.register(self.handle_set_gen_mode_simple, F.data == "set_gen_mode_simple")
        self.router.callback_query.register(self.handle_set_gen_mode_advanced, F.data == "set_gen_mode_advanced")
        self.router.callback_query.register(self.handle_back_to_categories, F.data == "back_to_categories")
        self.router.callback_query.register(self.handle_back_to_main_menu, F.data == "back_to_main_menu")
        self.router.callback_query.register(self.handle_back_to_purpose, F.data == "back_to_purpose")
        self.router.callback_query.register(self.handle_skip_additional_params, F.data == "skip_additional_params")
        self.router.callback_query.register(self.handle_back_to_generation, F.data == "back_to_generation")
        self.router.callback_query.register(self.handle_change_params, F.data == "change_params")
        self.router.callback_query.register(self.handle_change_additional_params, F.data == "change_additional_params")

    async def show_categories_command(self, message: Message):
        """Обработка команды /categories"""
        await self.show_categories(message)
    async def handle_start_button(self, callback: CallbackQuery):
        """Обработка кнопки 'Начать' из главного меню"""
        await callback.answer()
        await self.show_categories(callback.message)

    async def handle_my_sessions(self, callback: CallbackQuery):
        """Обработка кнопки 'Мои сессии' из главного меню"""
        await callback.answer()

        # Используем SessionHandler для показа сессий
        from app.bot.handlers.session_handler import SessionHandler
        session_handler = SessionHandler(self.config, self.services, self.repositories)
        await session_handler.show_user_sessions(callback.message)

    async def handle_back_to_generation(self, callback: CallbackQuery):
        """Возврат к генерации после изменения параметров"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # В зависимости от режима показываем соответствующую кнопку
        if session.generation_mode == 'simple':
            builder = InlineKeyboardBuilder()
            builder.button(text="🚀 Сгенерировать заголовок", callback_data="generate_title")
            builder.adjust(1)

            # Получаем название категории
            category_name = self._get_category_name(session.category_id)

            text = "✅ <b>Параметры обновлены!</b>\n\n"
            text += f"📋 <b>Параметры товара:</b>\n"
            text += f"• <b>Категория:</b> {category_name}\n"
            text += f"• <b>Назначение:</b> {session.purpose}\n"

            if session.additional_params:
                text += f"• <b>Доп. параметры:</b> {', '.join(session.additional_params)}\n\n"
            else:
                text += f"• <b>Доп. параметры:</b> не указаны\n\n"

            text += "Нажмите кнопку ниже чтобы сгенерировать новый заголовок:"

            await callback.message.edit_text(
                text,
                reply_markup=builder.as_markup()
            )
        else:
            # Для продвинутого режима проверяем, собраны ли данные
            if getattr(session, 'current_step', '') == "data_scraped":
                builder = InlineKeyboardBuilder()
                builder.button(text="🤖 Сгенерировать заголовок", callback_data="generate_title")
                builder.adjust(1)

                await callback.message.edit_text(
                    "✅ <b>Параметры обновлены!</b>\n\n"
                    "Нажмите кнопку ниже чтобы сгенерировать новый заголовок:",
                    reply_markup=builder.as_markup()
                )
            else:
                builder = InlineKeyboardBuilder()
                builder.button(text="🔍 Собрать данные", callback_data="collect_data")
                builder.adjust(1)

                await callback.message.edit_text(
                    "✅ <b>Параметры обновлены!</b>\n\n"
                    "Для продвинутой генерации сначала соберите данные:",
                    reply_markup=builder.as_markup()
                )

        await callback.answer()

    async def handle_back_to_purpose(self, callback: CallbackQuery):
        """Возврат к выбору назначения"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Получаем данные категории
        category_id = session.category_id
        if not self.categories:
            await self.load_categories_from_db()

        category_data = self.categories.get(category_id)
        if not category_data:
            await callback.answer("❌ Категория не найдена")
            return

        # Показываем выбор назначения снова
        builder = InlineKeyboardBuilder()
        for purpose_id, purpose_name in category_data["purposes"].items():
            builder.button(
                text=purpose_name,
                callback_data=f"purpose_{category_id}_{purpose_id}"
            )

        builder.button(text="↩️ Назад к категориям", callback_data="back_to_categories")
        builder.adjust(1)

        await callback.message.edit_text(
            f"✅ <b>Выбрана категория:</b> {category_data['name']}\n\n"
            f"📝 {category_data['description']}\n\n"
            "🎯 <b>Теперь выберите назначение товара:</b>",
            reply_markup=builder.as_markup()
        )

        await callback.answer()

    async def handle_change_additional_params(self, callback: CallbackQuery):
        """Изменение дополнительных параметров"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Просим ввести новые дополнительные параметры
        await callback.message.edit_text(
            f"📝 <b>Текущие дополнительные параметры:</b>\n"
            f"{', '.join(session.additional_params) if session.additional_params else 'нет'}\n\n"
            "✏️ <b>Введите новые дополнительные параметры:</b>\n"
            "<i>Напишите через запятую, например: 'высокая производительность, AMOLED дисплей, долгая батарея'</i>\n\n"
            "🔸 Или отправьте <code>нет</code> чтобы оставить без доп. параметров\n"
            "🔸 Для отмены отправьте <code>отмена</code>",
            parse_mode="HTML"
        )

        # Устанавливаем специальный флаг в сессии для отслеживания состояния изменения параметров
        session.is_changing_params = True
        session_repo.update(
            session.id,
            is_changing_params=True
        )

        await callback.answer()

    # Добавьте этот метод в класс CategoryHandler:

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

    async def handle_update_additional_params(self, message: Message):
        """Обработка обновления дополнительных параметров"""
        user_id = message.from_user.id

        # Игнорируем команды
        if message.text and message.text.startswith('/'):
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session or not getattr(session, 'is_changing_params', False):
            # Не наш шаг
            return

        params_text = message.text.strip().lower()

        # Проверяем отмену
        if params_text == "отмена":
            session.is_changing_params = False
            session_repo.update(session.id, is_changing_params=False)

            await message.answer("❌ Изменение параметров отменено")
            return

        additional_params = []

        if params_text != "нет":
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

        # Показываем обновленные параметры
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Сгенерировать с новыми параметрами", callback_data="generate_title")
        builder.button(text="📝 Изменить еще раз", callback_data="change_additional_params")
        builder.button(text="↩️ Назад к параметрам", callback_data="change_params")
        builder.adjust(1)

        await message.answer(
            f"✅ <b>Дополнительные параметры обновлены:</b>\n"
            f"{', '.join(additional_params) if additional_params else 'нет'}\n\n"
            "Что делаем дальше?",
            reply_markup=builder.as_markup()
        )

    async def handle_back_to_categories(self, callback: CallbackQuery):
        """Возврат к выбору категорий"""
        await callback.answer()

        # Получаем выбранные параметры для отображения
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

                if session.purpose:
                    welcome_text += f"\n✅ <b>Назначение:</b> {session.purpose}"

                if session.additional_params:
                    welcome_text += f"\n✅ <b>Доп. параметры:</b> {', '.join(session.additional_params)}"

        # Редактируем существующее сообщение
        await callback.message.edit_text(
            welcome_text,
            reply_markup=builder.as_markup()
        )

    async def handle_change_params(self, callback: CallbackQuery):
        """Изменение параметров товара"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Показываем текущие параметры с кнопками навигации
        builder = InlineKeyboardBuilder()
        builder.button(text="📝 Изменить доп. параметры", callback_data="change_additional_params")
        builder.button(text="↩️ Назад к генерации", callback_data="back_to_generation")
        builder.button(text="🏠 В главное меню", callback_data="back_to_main_menu")
        builder.adjust(1)

        category_name = self._get_category_name(session.category_id)

        await callback.message.edit_text(
            f"📋 <b>Текущие параметры товара:</b>\n\n"
            f"📁 <b>Категория:</b> {category_name}\n"
            f"🎯 <b>Назначение:</b> {session.purpose}\n"
            f"📝 <b>Доп. параметры:</b> {', '.join(session.additional_params) if session.additional_params else 'нет'}\n\n"
            f"Выберите что хотите изменить:",
            reply_markup=builder.as_markup()
        )

        await callback.answer()


    async def handle_start_generation(self, callback: CallbackQuery):
        """Обработка кнопки "Начать генерацию" в зависимости от режима"""
        user_id = callback.from_user.id
        mode = callback.data.replace("start_generation_", "")

        await callback.answer()

        if 'session_repo' not in self.repositories:
            await callback.message.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.message.answer("❌ Сессия не найдена")
            return

        # Проверяем, что режим совпадает
        if session.generation_mode != mode:
            await callback.message.answer("❌ Несоответствие режимов генерации")
            return

        if mode == 'simple':
            # Для простой генерации: сразу запускаем генерацию заголовка
            await callback.message.edit_text("🚀 <b>Запускаю простую генерацию...</b>")

            # Передаем управление в generation_handler
            # Нам нужно получить доступ к generation_handler
            # Для этого лучше всего отправить сообщение, которое обработается generation_handler
            await callback.message.answer("Запускаю генерацию контента...")
            # Или создаем искусственный CallbackQuery для generation_handler
            await self._trigger_simple_generation(callback.message, session)

        else:  # advanced
            # Для продвинутой генерации: запускаем сбор данных
            await callback.message.edit_text("🔍 <b>Запускаю сбор данных с MPStats...</b>")

            # Здесь будет логика запуска скрапера
            # Пока заглушка - перенаправляем в generation_handler
            await callback.message.answer("Сбор данных запущен...")
            await self._trigger_advanced_generation(callback.message, session)

    async def _trigger_simple_generation(self, message: Message, session):
        """Запуск простой генерации через generation_handler"""
        # Нам нужен доступ к generation_handler
        # Лучше всего через бота
        from app.bot.handlers import generation_handler

        # Альтернатива: отправим команду /generate_simple
        await message.answer("Используйте /generate для запуска генерации")
        # Или создадим искусственное сообщение
        # fake_message = Message(...)
        # await generation_handler._generate_title_simple(fake_message, session)

    async def load_categories_from_db(self):
        """Загрузка категорий из базы данных"""
        try:
            category_repo = self.repositories.get('category_repo')
            if not category_repo:
                self.logger.error("❌ Category repository not found!")
                return

            # Загружаем все категории
            categories = category_repo.get_all()

            if not categories:
                self.logger.warning("⚠️ No categories found in database!")
                return

            # Преобразуем в удобный формат
            self.categories = {}
            for category in categories:
                self.categories[category.id] = {
                    "name": category.name,
                    "description": category.description,
                    "purposes": category.purposes if category.purposes else {}
                }

            self.logger.info(f"✅ Загружено {len(self.categories)} категорий из базы данных")

        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки категорий: {e}")
    async def show_generation_mode_selection(self, message: Message):
        """Показать выбор способа генерации после заполнения параметров"""
        user_id = message.from_user.id
        self.logger.info(f"Пользователь {user_id} выбирает способ генерации")

        if 'session_repo' not in self.repositories:
            await message.answer("❌ Ошибка: репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await message.answer("❌ Сначала завершите настройку товара")
            return

        if session.current_step != "params_added":
            await message.answer("❌ Сначала укажите дополнительные параметры")
            return

        # Показываем выбор способа генерации
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Простая генерация", callback_data="set_gen_mode_simple")
        builder.button(text="🤖 Продвинутая генерация", callback_data="set_gen_mode_advanced")
        builder.adjust(1)

        await message.answer(
            "🎛️ <b>Выберите способ генерации контента:</b>\n\n"
            "<b>🚀 Простая генерация:</b>\n"
            "• Быстрое создание контента\n"
            "• На основе категории и назначения\n"
            "• Использует только OpenAI API\n\n"

            "<b>🤖 Продвинутая генерация:</b>\n"
            "• Анализ ключевых слов с MPStats\n"
            "• Глубокая оптимизация для маркетплейсов\n"
            "• Использует MPStats + OpenAI API\n\n"

            "<i>Продвинутая генерация дает более точные и оптимизированные результаты.</i>",
            reply_markup=builder.as_markup()
        )


    async def handle_go_to_generate(self, callback: CallbackQuery):
        """Перейти к генерации"""
        user_id = callback.from_user.id
        await callback.answer("✅ Способ генерации сохранен")
        await callback.message.answer("Теперь используйте команду /generate для создания контента")

    async def handle_set_gen_mode_simple(self, callback: CallbackQuery):
        """Установить простой способ генерации"""
        await self._set_generation_mode(callback, 'simple')

    async def handle_set_gen_mode_advanced(self, callback: CallbackQuery):
        """Установить продвинутый способ генерации"""
        await self._set_generation_mode(callback, 'advanced')

    # В category_handler.py - метод _set_generation_mode:
    async def _set_generation_mode(self, callback: CallbackQuery, mode: str):
        """Общий метод установки способа генерации"""
        user_id = callback.from_user.id
        self.logger.info(f"Пользователь {user_id} выбрал способ генерации: {mode}")

        if 'session_repo' not in self.repositories:
            await callback.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сначала завершите настройку товара")
            return

        try:
            # Обновляем сессию
            session.generation_mode = mode
            session.current_step = "generation_mode_selected"

            session_repo.update(
                session.id,
                generation_mode=mode,
                current_step="generation_mode_selected"
            )

            mode_name = "Простая" if mode == 'simple' else "Продвинутая"
            mode_icon = "🚀" if mode == 'simple' else "🤖"

            # Получаем название категории
            category_name = self._get_category_name(session.category_id)

            # Формируем текст со ВСЕМИ параметрами
            text = f"✅ <b>Способ генерации установлен:</b> {mode_name}\n\n"
            text += f"📋 <b>Параметры товара:</b>\n"
            text += f"• <b>Категория:</b> {category_name}\n"
            text += f"• <b>Назначение:</b> {session.purpose}\n"

            if session.additional_params:
                text += f"• <b>Доп. параметры:</b> {', '.join(session.additional_params)}\n\n"
            else:
                text += f"• <b>Доп. параметры:</b> не указаны\n\n"

            if mode == 'simple':
                text += "🚀 <b>Простая генерация:</b>\n"
                text += "• Создание заголовка на основе указанных параметров\n"
                text += "• Без анализа ключевых слов\n"
                text += "• Быстро и просто\n\n"
                text += "Нажмите кнопку ниже чтобы сгенерировать заголовок:"

                builder = InlineKeyboardBuilder()
                builder.button(text="🚀 Сгенерировать заголовок", callback_data="generate_title")
            else:
                text += "🤖 <b>Продвинутая генерация:</b>\n"
                text += "• Анализ ключевых слов с MPStats\n"
                text += "• Глубокая оптимизация для маркетплейсов\n"
                text += "• Более точные результаты\n\n"
                text += "Нажмите кнопку ниже чтобы начать сбор данных:"

                builder = InlineKeyboardBuilder()
                builder.button(text="🔍 Собрать данные", callback_data="collect_data")

            # Добавляем кнопки навигации
            builder.button(text="↩️ Изменить параметры", callback_data="change_params")
            builder.button(text="🏠 В главное меню", callback_data="back_to_main_menu")
            builder.adjust(1)

            await callback.message.edit_text(
                text,
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            self.logger.error(f"Ошибка установки способа генерации: {e}")
            await callback.answer("❌ Ошибка сохранения")

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
                welcome_text += f"\n✅ <b>Назначение:</b> {session.purpose}"

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

        # Проверяем, загружены ли категории
        if not self.categories:
            await self.load_categories_from_db()

        category_data = self.categories.get(category_id)
        if not category_data:
            await callback.answer("❌ Категория не найдена")
            return

        # Создаем/обновляем сессию пользователя
        session_repo = self.repositories['session_repo']
        try:
            # Получаем или создаем сессию
            existing_session = session_repo.get_active_session(user_id)

            if existing_session:
                # Обновляем существующую сессию
                existing_session.category_id = category_id
                session_repo.update(
                    existing_session.id,
                    category_id=category_id,
                    current_step="category_selected"
                )
                session = existing_session
            else:
                # Создаем новую сессию
                session = session_repo.create_new_session(
                    user_id=user_id,
                    category_id=category_id,
                    current_step="category_selected"
                )

            # Показываем выбор назначения с кнопкой "Назад"
            builder = InlineKeyboardBuilder()
            for purpose_id, purpose_name in category_data["purposes"].items():
                builder.button(
                    text=purpose_name,
                    callback_data=f"purpose_{category_id}_{purpose_id}"
                )

            # Кнопка "Назад" к выбору категорий
            builder.button(text="↩️ Назад к категориям", callback_data="back_to_categories")
            builder.adjust(1)

            # Формируем текст с текущими параметрами
            text = f"✅ <b>Выбрана категория:</b> {category_data['name']}\n\n"
            text += f"📝 {category_data['description']}\n\n"

            if session.purpose:
                text += f"✅ <b>Назначение:</b> {session.purpose}\n"

            if session.additional_params:
                text += f"✅ <b>Доп. параметры:</b> {', '.join(session.additional_params)}\n\n"

            text += "🎯 <b>Теперь выберите назначение товара:</b>"

            await callback.message.edit_text(
                text,
                reply_markup=builder.as_markup()
            )
            await callback.answer()

        except Exception as e:
            self.logger.error(f"❌ Error creating/updating session: {e}")
            await callback.message.edit_text(
                "❌ <b>Ошибка при создании сессии</b>\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )
            await callback.answer()

    async def handle_purpose_select(self, callback: CallbackQuery):
        """Обработка выбора назначения"""
        user_id = callback.from_user.id
        data_parts = callback.data.replace("purpose_", "").split("_")

        if len(data_parts) != 2:
            await callback.answer("❌ Ошибка данных")
            return

        category_id, purpose_id = data_parts

        # Проверяем, загружены ли категории
        if not self.categories:
            await self.load_categories_from_db()

        category_data = self.categories.get(category_id)

        if not category_data:
            await callback.answer("❌ Категория не найдена")
            return

        purpose_name = category_data["purposes"].get(purpose_id)
        if not purpose_name:
            await callback.answer("❌ Назначение не найдено")
            return

        # Сначала создаем/получаем пользователя
        user_repo = self.repositories['user_repo']
        user = user_repo.get_or_create(
            telegram_id=user_id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name
        )

        # Обновляем сессию
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Сохраняем purpose как строку с названием
        session.purpose = purpose_name
        session.current_step = "purpose_selected"
        session_repo.update(
            session.id,
            purpose=purpose_name,
            current_step="purpose_selected"
        )

        await self.show_additional_params_request(callback.message, session)
        await callback.answer()

    async def handle_back_to_categories(self, callback: CallbackQuery):
        """Возврат к выбору категорий"""
        await callback.answer()
        await self.show_categories(callback.message, from_back=True)

    # В category_handler.py изменим метод handle_back_to_main_menu:
    async def handle_back_to_main_menu(self, callback: CallbackQuery):
        """Возврат в главное меню без сброса сессии"""
        await callback.answer()

        # НЕ СБРАСЫВАЕМ СЕССИЮ - удаляем эту часть
        # user_id = callback.from_user.id
        # session_repo = self.repositories.get('session_repo')
        # if session_repo:
        #     session_repo.deactivate_all_sessions(user_id)

        # Просто показываем приветственное сообщение
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
        """Пропуск дополнительных параметров"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return


        session.additional_params = []
        session.current_step = "params_added"

        session_repo.update(
            session.id,
            additional_params=[],
            current_step="params_added"
        )

        # Показываем выбор способа генерации
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Простая генерация", callback_data="set_gen_mode_simple")
        builder.button(text="🤖 Продвинутая генерация", callback_data="set_gen_mode_advanced")
        builder.adjust(1)

        await callback.message.edit_text(
            "✅ <b>Дополнительные параметры не указаны</b>\n\n"
            "🎛️ <b>Выберите способ генерации контента:</b>\n\n"
            "<b>🚀 Простая генерация:</b>\n"
            "• Быстрое создание контента\n"
            "• На основе категории и назначения\n\n"
            "<b>🤖 Продвинутая генерация:</b>\n"
            "• Анализ ключевых слов с MPStats\n"
            "• Глубокая оптимизация\n\n"
            "<i>Продвинутая генерация дает более точные результаты.</i>",
            reply_markup=builder.as_markup()
        )

        await callback.answer()


    async def handle_additional_params(self, message: Message):
        """Обработка ввода дополнительных параметров"""
        user_id = message.from_user.id

        # ИГНОРИРУЕМ КОМАНДЫ
        if message.text and message.text.startswith('/'):
            self.logger.info(f"Игнорируем команду: {message.text}")
            return

        # Проверяем активную сессию
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        self.logger.info(f"=== handle_additional_params: user_id={user_id}, session={session is not None}")
        if session:
            self.logger.info(f"Текущий шаг сессии: {getattr(session, 'current_step', 'N/A')}")
            self.logger.info(f"is_changing_params: {getattr(session, 'is_changing_params', False)}")

        # Проверяем два сценария:
        # 1. Стандартный сценарий: пользователь только что выбрал назначение
        # 2. Сценарий изменения параметров: установлен флаг is_changing_params
        if not session:
            # Не выводим сообщение, если это не наш шаг
            return

        # Сценарий 1: стандартный ввод параметров после выбора назначения
        if session.current_step == "purpose_selected":
            await self._handle_initial_params_input(message, session)
            return

        # Сценарий 2: изменение параметров после генерации
        if getattr(session, 'is_changing_params', False):
            await self._handle_update_params_input(message, session)
            return

        # Если не наш шаг, просто выходим
        return

    async def _handle_initial_params_input(self, message: Message, session):
        """Обработка первоначального ввода параметров"""
        params_text = message.text.strip().lower()
        additional_params = []

        if params_text != "нет":
            # Разбиваем параметры по запятой
            additional_params = [param.strip() for param in params_text.split(',') if param.strip()]

            success_message = f"✅ <b>Дополнительные параметры сохранены:</b>\n{', '.join(additional_params)}"
        else:
            success_message = "✅ <b>Дополнительные параметры не указаны</b>"

        # Сохраняем параметры в сессии
        session.additional_params = additional_params
        session.current_step = "params_added"

        self.logger.info(
            f"🔄 Обновляем сессию {session.id}: additional_params={additional_params}, current_step=params_added")

        # Обновляем сессию в базе данных
        session_repo = self.repositories['session_repo']
        updated_session = session_repo.update(
            session.id,
            additional_params=additional_params,
            current_step="params_added"
        )

        if updated_session:
            self.logger.info(f"✅ Сессия обновлена: ID={updated_session.id}, Шаг={updated_session.current_step}")
        else:
            self.logger.error("❌ Сессия не обновлена!")

        # Показываем выбор способа генерации
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Простая генерация", callback_data="set_gen_mode_simple")
        builder.button(text="🤖 Продвинутая генерация", callback_data="set_gen_mode_advanced")
        builder.adjust(1)

        await message.answer(
            f"{success_message}\n\n"
            "🎛️ <b>Выберите способ генерации контента:</b>\n\n"
            "<b>🚀 Простая генерация:</b>\n"
            "• Быстрое создание контента\n"
            "• На основе категории и назначения\n"
            "• Использует только OpenAI API\n\n"

            "<b>🤖 Продвинутая генерация:</b>\n"
            "• Анализ ключевых слов с MPStats\n"
            "• Глубокая оптимизация для маркетплейсов\n"
            "• Использует MPStats + OpenAI API\n\n"

            "<i>Продвинутая генерация дает более точные и оптимизированные результаты.</i>",
            reply_markup=builder.as_markup()
        )

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
            f"🎯 <b>Назначение:</b> {session.purpose}\n"
            f"📝 <b>Доп. параметры:</b> {', '.join(additional_params) if additional_params else 'нет'}\n\n"
            "Что делаем дальше?",
            reply_markup=builder.as_markup()
        )

    async def start_scraping(self, message: Message):
        """Запуск скрапинга"""
        user_id = message.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session or session.current_step != "params_added":
            await message.answer(
                "⚠️ <b>Сначала настройте параметры</b>\n\n"
                "Используйте <code>/categories</code> чтобы выбрать категорию, назначение и параметры."
            )
            return

        # Запускаем скрапинг
        await message.answer("⏳ <b>Начинаю сбор данных с MPStats...</b>")

        # Здесь будет логика запуска скрапера
        # Пока просто заглушка
        await message.answer(
            "✅ <b>Скрапер запущен!</b>\n"
            "Это тестовое сообщение. Реальная логика скрапера будет добавлена позже."
        )

    async def reset_session(self, message: Message):
        """Сброс сессии"""
        user_id = message.from_user.id

        session_repo = self.repositories['session_repo']
        active_sessions = session_repo.get_active_session(user_id)
        if active_sessions:
            # Если get_active_session возвращает одну сессию, а не список
            if isinstance(active_sessions, list):
                for session in active_sessions:
                    session_repo.update(session.id, is_active=False)
            else:
                session_repo.update(active_sessions.id, is_active=False)

        await message.answer(
            "🔄 <b>Сессия сброшена</b>\n"
            "Начните заново с <code>/categories</code>"
        )