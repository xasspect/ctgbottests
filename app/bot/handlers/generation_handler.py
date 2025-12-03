import asyncio
import logging
from aiogram.filters import Command
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class GenerationHandler(BaseMessageHandler):
    """Обработчик генерации контента"""

    def __init__(self, services: dict, repositories: dict):
        super().__init__(services, repositories)
        self.router = Router()
        self.logger = logging.getLogger(__name__)

    async def register(self, dp):
        dp.include_router(self.router)
        self.router.message.register(self.handle_additional_params, F.text & ~F.command)
        self.router.callback_query.register(self.handle_generate_title, F.data == "generate_title")
        self.router.callback_query.register(self.handle_regenerate_title, F.data == "regenerate_title")
        self.router.callback_query.register(self.handle_approve_title, F.data.startswith("approve_title_"))
        # Добавляем обработчики для генерации описаний
        self.router.callback_query.register(self.handle_generate_short_desc, F.data.startswith("generate_short_"))
        self.router.callback_query.register(self.handle_generate_long_desc, F.data.startswith("generate_long_"))
        self.router.callback_query.register(self.handle_generate_both_desc, F.data.startswith("generate_both_"))
        self.router.message.register(self.show_generate_options, Command(commands=["generate"]))

    async def show_generate_options(self, message: Message):
        """Показать опции генерации"""
        user_id = message.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session or session.current_step != "params_added":
            await message.answer(
                "⚠️ Сначала завершите настройку товара:\n"
                "1. <code>/categories</code> - выбрать категорию и назначение\n"
                "2. Укажите дополнительные параметры (опционально)\n"
                "3. Затем используйте <code>/generate</code>"
            )
            return

        # Получаем название категории из наших данных
        category_name = self._get_category_display_name(session.category_id)

        # Показываем кнопку для начала генерации
        builder = InlineKeyboardBuilder()
        builder.button(text="🎯 Сгенерировать контент", callback_data="generate_title")

        await message.answer(
            "📊 <b>Параметры генерации:</b>\n\n"
            f"• <b>Категория:</b> {category_name}\n"
            f"• <b>Назначение:</b> {session.purpose}\n"
            f"• <b>Доп. параметры:</b> {', '.join(session.additional_params) if session.additional_params else 'нет'}\n\n"
            "Нажмите кнопку ниже чтобы начать генерацию:",
            reply_markup=builder.as_markup()
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

    async def handle_additional_params(self, message: Message):
        """Обработка дополнительных параметров"""
        user_id = message.from_user.id
        params_text = message.text.strip().lower()

        # Проверяем активную сессию
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session or session.current_step != "purpose_added":
            return

        additional_params = []

        if params_text != "нет":
            # Разбиваем параметры по запятой
            additional_params = [param.strip() for param in params_text.split(',') if param.strip()]

            await message.answer(
                f"✅ <b>Дополнительные параметры сохранены:</b>\n"
                f"{', '.join(additional_params)}\n\n"
                "🔄 <b>Начинаю генерацию контента...</b>"
            )
        else:
            await message.answer("🔄 <b>Начинаю генерацию контента без дополнительных параметров...</b>")

        # Сохраняем параметры и начинаем генерацию
        session.additional_params = additional_params
        session.current_step = "params_added"
        session_repo.update(session.id, additional_params=additional_params, current_step="params_added")

        # Показываем кнопку для начала генерации
        builder = InlineKeyboardBuilder()
        builder.button(text="🎯 Сгенерировать заголовок", callback_data="generate_title")

        await message.answer(
            "📊 <b>Готов к генерации!</b>\n\n"
            f"• <b>Категория:</b> {self._get_category_name(session.category_id)}\n"
            f"• <b>Назначение:</b> {session.purpose}\n"
            f"• <b>Доп. параметры:</b> {', '.join(additional_params) if additional_params else 'нет'}\n\n"
            "Нажмите кнопку ниже чтобы начать генерацию:",
            reply_markup=builder.as_markup()
        )

    # app/bot/handlers/generation_handler.py (обновляем методы)
    async def handle_generate_title(self, callback: CallbackQuery):
        """Генерация заголовка с реальными сервисами"""
        user_id = callback.from_user.id

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
            content_service = self.services['content']

            category_data = {
                'system_prompt_filter': category.system_prompt_filter,
                'system_prompt_title': category.system_prompt_title
            }

            result = await content_service.generate_content_workflow(
                category_name=category.name,
                purpose=session.purpose,
                additional_params=session.additional_params,
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
            self.logger.error(f"❌ Ошибка генерации: {e}")
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

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        await callback.message.edit_text("📄 <b>Генерирую оба описания...</b>")

        try:
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)
            content_service = self.services['content']

            category_data = {
                'system_prompt_description': category.system_prompt_description
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
            content_service = self.services['content']

            category_data = {
                'system_prompt_description': category.system_prompt_description
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
        category_repo = self.repositories['category_repo']
        category = category_repo.get_by_id(category_id)
        return category.name if category else "Неизвестно"

    async def _get_mock_keywords(self, category: str, purpose: str) -> list:
        """Заглушка для получения ключевых слов"""
        await asyncio.sleep(1)  # Имитация задержки

        mock_keywords = {
            "Электроника/Смартфоны": [
                "смартфон", "игровой", "производительный", "камера", "батарея",
                "AMOLED", "процессор", "память", "быстрая зарядка", "Android"
            ],
            "Одежда/Обувь": [
                "одежда", "обувь", "стильная", "комфортная", "качественная",
                "модная", "удобная", "прочная", "брендовая", "тренд"
            ]
        }

        return mock_keywords.get(category, ["качественный", "популярный", purpose])

    async def _filter_keywords(self, keywords: list, additional_params: list) -> list:
        """Заглушка для фильтрации ключевых слов"""
        await asyncio.sleep(1)

        # Простая фильтрация - берем первые 8 слов
        filtered = keywords[:8]

        # Добавляем дополнительные параметры
        if additional_params:
            filtered.extend(additional_params[:3])

        return list(set(filtered))  # Убираем дубли

    async def _generate_mock_title(self, category: str, purpose: str, keywords: list) -> str:
        """Заглушка для генерации заголовка"""
        await asyncio.sleep(1)

        templates = {
            "Электроника/Смартфоны": [
                f"Смартфон {purpose} с {keywords[2]} и {keywords[3]}",
                f"Мощный смартфон для {purpose} - {keywords[1]}, {keywords[4]}",
                f"{keywords[0].title()} для {purpose}: {keywords[2]}, {keywords[3]}, {keywords[4]}"
            ],
            "Одежда/Обувь": [
                f"{category.split('/')[0]} для {purpose} - {keywords[1]}, {keywords[2]}",
                f"Стильная {category.split('/')[0].lower()} для {purpose}",
                f"{keywords[0].title()} {purpose}: {keywords[1]}, {keywords[2]}, комфорт"
            ]
        }

        import random
        template = templates.get(category, templates["Электроника/Смартфоны"])
        return random.choice(template)