import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class GenerationHandler(BaseMessageHandler):
    """Обработчик генерации контента"""

    def __init__(self, services: dict, repositories: dict):
        super().__init__(services, repositories)
        self.router = Router()

    async def register(self, dp):
        dp.include_router(self.router)
        self.router.message.register(self.handle_additional_params, F.text & ~F.command)
        self.router.callback_query.register(self.handle_generate_title, F.data == "generate_title")
        self.router.callback_query.register(self.handle_regenerate_title, F.data == "regenerate_title")
        self.router.callback_query.register(self.handle_approve_title, F.data.startswith("approve_title_"))

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

    async def handle_generate_title(self, callback: CallbackQuery):
        """Генерация заголовка"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        await callback.message.edit_text("🔍 <b>Получаю ключевые слова из MPStats...</b>")

        try:
            # Имитация работы с MPStats
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            # Получаем ключевые слова (пока заглушка)
            keywords = await self._get_mock_keywords(category.name, session.purpose)

            await callback.message.edit_text(
                f"✅ <b>Получено {len(keywords)} ключевых слов</b>\n"
                f"🤖 <b>Фильтрую через AI...</b>"
            )

            # Фильтрация ключевых слов (заглушка)
            filtered_keywords = await self._filter_keywords(keywords, session.additional_params)

            await callback.message.edit_text(
                f"✅ <b>Отфильтровано до {len(filtered_keywords)} релевантных слов</b>\n"
                f"🎯 <b>Генерирую заголовок...</b>"
            )

            # Генерация заголовка (заглушка)
            title = await self._generate_mock_title(category.name, session.purpose, filtered_keywords)

            # Сохраняем заголовок в сессии
            session.generated_title = title
            session.keywords = filtered_keywords
            session.current_step = "title_generated"
            session_repo.update(
                session.id,
                generated_title=title,
                keywords=filtered_keywords,
                current_step="title_generated"
            )

            # Показываем заголовок с кнопками
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Принять", callback_data=f"approve_title_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data="regenerate_title")
            builder.adjust(1)

            await callback.message.edit_text(
                f"📝 <b>Предлагаю заголовок:</b>\n\n"
                f"<code>{title}</code>\n\n"
                f"🔑 <b>Ключевые слова:</b> {', '.join(filtered_keywords[:8])}...",
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