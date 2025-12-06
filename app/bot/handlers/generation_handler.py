import asyncio
import logging
from aiogram.filters import Command
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler
from app.config.config import config


class GenerationHandler(BaseMessageHandler):
    """Обработчик генерации контента"""

    def __init__(self, config, services: dict, repositories: dict):
        super().__init__(config, services, repositories)
        self.router = Router()
        self.logger = logging.getLogger(__name__)

    async def register(self, dp):
        dp.include_router(self.router)
        # Убрана регистрация handle_additional_params - это в CategoryHandler
        self.router.callback_query.register(self.handle_generate_title, F.data == "generate_title")
        self.router.callback_query.register(self.handle_regenerate_title, F.data == "regenerate_title")
        self.router.callback_query.register(self.handle_approve_title, F.data.startswith("approve_title_"))
        # Добавляем обработчики для генерации описаний
        self.router.callback_query.register(self.handle_generate_short_desc, F.data.startswith("generate_short_"))
        self.router.callback_query.register(self.handle_generate_long_desc, F.data.startswith("generate_long_"))
        self.router.callback_query.register(self.handle_generate_both_desc, F.data.startswith("generate_both_"))
        self.router.message.register(self.show_generate_options, Command(commands=["generate"]))

    async def show_generate_options(self, message: Message):
        """Показать опции генерации и запустить скрапер"""
        user_id = message.from_user.id
        self.logger.info(f"=== ВЫЗВАН /generate для пользователя {user_id} ===")
        self.logger.info(f"Текст сообщения: '{message.text}'")

        self.logger.info(f"Репозитории доступны: {list(self.repositories.keys())}")
        self.logger.info(f"Сервисы доступны: {list(self.services.keys())}")

        # Проверяем наличие репозитория
        if 'session_repo' not in self.repositories:
            self.logger.error("❌ session_repo не найден в repositories!")
            await message.answer("❌ Ошибка: репозиторий сессий не инициализирован")
            return

        session_repo = self.repositories['session_repo']
        self.logger.info(f"session_repo тип: {type(session_repo)}")

        try:
            # Получаем сессию с отладочной информацией
            self.logger.info(f"Запрашиваем активную сессию для user_id={user_id}")
            session = session_repo.get_active_session(user_id)

            # Логируем полученную сессию
            if session:
                self.logger.info(f"✅ Сессия получена: ID={session.id}")
                self.logger.info(f"  Категория: {getattr(session, 'category_id', 'N/A')}")
                self.logger.info(f"  Назначение: {getattr(session, 'purpose', 'N/A')}")
                self.logger.info(f"  Текущий шаг: {getattr(session, 'current_step', 'N/A')}")
                self.logger.info(f"  Доп. параметры: {getattr(session, 'additional_params', 'N/A')}")
                self.logger.info(f"  Активна: {getattr(session, 'is_active', 'N/A')}")
            else:
                self.logger.warning("❌ Сессия не найдена или не активна")
        except Exception as e:
            print(e)

            # [Остальной код остается без изменений...]

        # Проверяем, есть ли сессия
        # Проверяем, есть ли сессия
        if not session:
            await message.answer(
                "⚠️ Сначала завершите настройку товара:\n"
                "1. <code>/categories</code> - выбрать категорию и назначение\n"
                "2. Укажите дополнительные параметры (опционально)\n"
                "3. Затем используйте <code>/generate</code>"
            )
            return

        # ВРЕМЕННО: пропускаем проверку current_step для тестирования
        # if session.current_step != "params_added":
        #     await message.answer(
        #         f"⚠️ Текущий шаг: {session.current_step}. Сначала завершите настройку:\n"
        #         "1. <code>/categories</code> - выбрать категорию и назначение\n"
        #         "2. Укажите дополнительные параметры (опционально)\n"
        #         "3. Затем используйте <code>/generate</code>"
        #     )
        #     return

        # Вместо этого просто логируем шаг
        self.logger.info(f"Шаг сессии: {session.current_step}, продолжаем...")

        # Получаем название категории из наших данных
        category_name = self._get_category_display_name(session.category_id)

        # Проверяем наличие скрапера
        if 'scraper' not in self.services:
            self.logger.error("❌ Скрапер сервис не найден в services!")
            await message.answer("❌ Ошибка: скрапер сервис не инициализирован")
            return

        scraper_service = self.services['scraper']

        # Запускаем скрапер для сбора данных
        await message.answer(f"🔍 <b>Начинаю сбор данных с MPStats для категории:</b> {category_name}")

        try:
            # Подготавливаем параметры для скрапера
            scraper_params = {
                'category': session.category_id,
                'purpose': session.purpose,
                'additional_params': session.additional_params if hasattr(session, 'additional_params') else [],
                'user_id': user_id,
                'session_id': session.id
            }

            self.logger.info(f"Запускаем скрапер с параметрами: {scraper_params}")

            # Запускаем скрапер
            downloaded_file = await scraper_service.scrape_categories(scraper_params)

            if downloaded_file:
                # Сохраняем путь к файлу в сессии
                session.scraped_file = downloaded_file
                session.current_step = "data_scraped"
                session_repo.update(
                    session.id,
                    scraped_file=downloaded_file,
                    current_step="data_scraped"
                )

                await message.answer(
                    f"✅ <b>Данные успешно собраны!</b>\n\n"
                    f"📁 Файл сохранен: <code>{downloaded_file}</code>\n\n"
                    "Теперь можно сгенерировать контент на основе собранных данных."
                )

                # Показываем кнопку для генерации контента
                builder = InlineKeyboardBuilder()
                builder.button(text="🎯 Сгенерировать заголовок", callback_data="generate_title")

                await message.answer(
                    "📊 <b>Параметры генерации:</b>\n\n"
                    f"• <b>Категория:</b> {category_name}\n"
                    f"• <b>Назначение:</b> {session.purpose}\n"
                    f"• <b>Доп. параметры:</b> {', '.join(session.additional_params) if hasattr(session, 'additional_params') and session.additional_params else 'нет'}\n"
                    f"• <b>Собранные данные:</b> ✅\n\n"
                    "Нажмите кнопку ниже чтобы начать генерацию контента:",
                    reply_markup=builder.as_markup()
                )
            else:
                await message.answer(
                    "❌ <b>Не удалось собрать данные с MPStats</b>\n\n"
                    "Попробуйте:\n"
                    "1. Проверить логин/пароль MPStats в настройках\n"
                    "2. Подождать и попробовать снова\n"
                    "3. Использовать заглушечные данные для тестирования"
                )

        except Exception as e:
            self.logger.error(f"❌ Ошибка при сборе данных: {e}", exc_info=True)
            await message.answer(
                f"❌ <b>Ошибка при сборе данных:</b>\n{str(e)[:200]}\n\n"
                "Попробуйте еще раз или обратитесь к администратору."
            )

    def _get_category_display_name(self, category_id: str) -> str:
        """Получить отображаемое название категории"""
        categories_data = {
            "electronics": "📱 Электроника",
            "clothing": "👕 Одежда и обувь",
            "home": "🏠 Дом и сад",
            "beauty": "💄 Красота и здоровье"
        }
        return categories_data.get(category_id, "Неизвестная категория")

    # Остальные методы оставляем без изменений, но добавляем проверки на существование репозиториев
    async def handle_generate_title(self, callback: CallbackQuery):
        """Генерация заголовка с реальными сервисами"""
        user_id = callback.from_user.id

        # Проверяем наличие репозиториев
        if 'session_repo' not in self.repositories or 'category_repo' not in self.repositories:
            await callback.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        await callback.message.edit_text("🔍 <b>Получаю ключевые слова из MPStats...</b>")

        try:
            # Получаем данные категории
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if not category:
                await callback.message.edit_text("❌ Категория не найдена")
                return

            # Используем сервис для генерации контента
            if 'content' not in self.services:
                await callback.message.edit_text("❌ Сервис генерации контента не инициализирован")
                return

            content_service = self.services['content']

            category_data = {
                'system_prompt_filter': getattr(category, 'system_prompt_filter', ''),
                'system_prompt_title': getattr(category, 'system_prompt_title', '')
            }

            result = await content_service.generate_content_workflow(
                category_name=category.name,
                purpose=session.purpose,
                additional_params=session.additional_params if hasattr(session, 'additional_params') else [],
                category_data=category_data
            )

            # Сохраняем результаты в сессии
            session.generated_title = result['title']
            session.keywords = result['keywords']
            session.current_step = "title_generated"
            session_repo.update(
                session.id,
                generated_title=result['title'],
                keywords=result['keywords'],
                current_step="title_generated"
            )

            # Показываем заголовок с кнопками
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Принять", callback_data=f"approve_title_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data="regenerate_title")
            builder.adjust(1)

            await callback.message.edit_text(
                f"📝 <b>Предлагаю заголовок:</b>\n\n"
                f"<code>{result['title']}</code>\n\n"
                f"🔑 <b>Ключевые слова:</b> {', '.join(result['keywords'][:8])}...",
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации: {e}", exc_info=True)
            await callback.message.edit_text(
                f"❌ <b>Ошибка генерации:</b> {str(e)}\n\n"
                "Попробуйте изменить параметры или начать заново с /reset"
            )

        await callback.answer()

    async def handle_generate_short_desc(self, callback: CallbackQuery):
        """Генерация краткого описания"""
        await self._generate_description(callback, "short")

    async def handle_generate_long_desc(self, callback: CallbackQuery):
        """Генерация подробного описания"""
        await self._generate_description(callback, "long")

    async def handle_generate_both_desc(self, callback: CallbackQuery):
        """Генерация обоих описаний"""
        session_id = callback.data.replace("generate_both_", "")

        if 'session_repo' not in self.repositories or 'category_repo' not in self.repositories:
            await callback.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        await callback.message.edit_text("📄 <b>Генерирую оба описания...</b>")

        try:
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if 'content' not in self.services:
                await callback.message.edit_text("❌ Сервис генерации контента не инициализирован")
                return

            content_service = self.services['content']

            category_data = {
                'system_prompt_description': getattr(category, 'system_prompt_description', '')
            }

            # Генерируем оба описания
            short_desc = await content_service.generate_description_workflow(
                session.generated_title, session.keywords, "short", category.name, category_data
            )

            long_desc = await content_service.generate_description_workflow(
                session.generated_title, session.keywords, "long", category.name, category_data
            )

            # Сохраняем в сессии
            session.short_description = short_desc
            session.long_description = long_desc
            session_repo.update(
                session.id,
                short_description=short_desc,
                long_description=long_desc
            )

            # Сохраняем в таблице generated_content
            if 'content_repo' in self.repositories:
                content_repo = self.repositories['content_repo']
                content_repo.create(
                    session_id=session.id,
                    user_id=session.user_id,
                    title=session.generated_title,
                    short_description=short_desc,
                    long_description=long_desc,
                    keywords=session.keywords,
                    category_id=session.category_id,
                    purpose=session.purpose
                )

            await callback.message.edit_text(
                f"✅ <b>Оба описания сгенерированы!</b>\n\n"
                f"📝 <b>Заголовок:</b>\n<code>{session.generated_title}</code>\n\n"
                f"📋 <b>Краткое описание:</b>\n{short_desc}\n\n"
                f"📖 <b>Подробное описание:</b>\n{long_desc}\n\n"
                f"💾 <b>Контент сохранен в истории</b>"
            )

        except Exception as e:
            await callback.message.edit_text(f"❌ <b>Ошибка генерации:</b> {str(e)}")

        await callback.answer()

    async def _generate_description(self, callback: CallbackQuery, desc_type: str):
        """Общий метод генерации описания"""
        session_id = callback.data.replace(f"generate_{desc_type}_", "")

        if 'session_repo' not in self.repositories or 'category_repo' not in self.repositories:
            await callback.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        type_name = "краткое" if desc_type == "short" else "подробное"
        await callback.message.edit_text(f"📄 <b>Генерирую {type_name} описание...</b>")

        try:
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if 'content' not in self.services:
                await callback.message.edit_text("❌ Сервис генерации контента не инициализирован")
                return

            content_service = self.services['content']

            category_data = {
                'system_prompt_description': getattr(category, 'system_prompt_description', '')
            }

            description = await content_service.generate_description_workflow(
                session.generated_title, session.keywords, desc_type, category.name, category_data
            )

            # Сохраняем в сессии
            if desc_type == "short":
                session.short_description = description
            else:
                session.long_description = description

            session_repo.update(
                session.id,
                **{f"{desc_type}_description": description}
            )

            # Показываем кнопки для дальнейших действий
            builder = InlineKeyboardBuilder()
            if desc_type == "short":
                builder.button(text="📖 Сгенерировать подробное", callback_data=f"generate_long_{session.id}")
            else:
                builder.button(text="📋 Сгенерировать краткое", callback_data=f"generate_short_{session.id}")

            builder.button(text="⚡ Оба описания", callback_data=f"generate_both_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data=f"regenerate_{desc_type}_{session.id}")
            builder.adjust(1)

            await callback.message.edit_text(
                f"✅ <b>{type_name.title()} описание:</b>\n\n{description}",
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            await callback.message.edit_text(f"❌ <b>Ошибка генерации:</b> {str(e)}")

        await callback.answer()

    async def handle_regenerate_title(self, callback: CallbackQuery):
        """Перегенерация заголовка"""
        await self.handle_generate_title(callback)

    async def handle_approve_title(self, callback: CallbackQuery):
        """Подтверждение заголовка"""
        session_id = callback.data.replace("approve_title_", "")

        if 'session_repo' not in self.repositories:
            await callback.answer("❌ Репозиторий сессий не инициализирован")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Показываем варианты генерации описаний
        builder = InlineKeyboardBuilder()
        builder.button(text="📋 Краткое описание", callback_data=f"generate_short_{session.id}")
        builder.button(text="📖 Подробное описание", callback_data=f"generate_long_{session.id}")
        builder.button(text="⚡ Оба описания", callback_data=f"generate_both_{session.id}")
        builder.adjust(1)

        await callback.message.edit_text(
            f"✅ <b>Заголовок принят!</b>\n\n"
            f"<code>{session.generated_title}</code>\n\n"
            "📄 <b>Выберите тип описания:</b>",
            reply_markup=builder.as_markup()
        )
        await callback.answer()

    def _get_category_name(self, category_id: str) -> str:
        """Получить название категории по ID"""
        if 'category_repo' not in self.repositories:
            return "Неизвестно"

        category_repo = self.repositories['category_repo']
        category = category_repo.get_by_id(category_id)
        return category.name if category else "Неизвестно"