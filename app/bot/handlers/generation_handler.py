# app/bot/handlers/generation_handler.py
import asyncio
import json
import logging
from aiogram.filters import Command
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class GenerationHandler(BaseMessageHandler):
    """Обработчик генерации контента"""

    def __init__(self, config, services: dict, repositories: dict):
        super().__init__(config, services, repositories)
        self.router = Router()
        self.logger = logging.getLogger(__name__)

    async def register(self, dp):
        dp.include_router(self.router)
        self.router.callback_query.register(self.handle_back_to_menu, F.data == "back_to_menu_from_generation")
        self.router.callback_query.register(self.handle_collect_data, F.data.startswith("collect_data_"))
        self.router.callback_query.register(self.handle_show_generation_menu,
                                            F.data.startswith("show_generation_menu_"))

    async def handle_collect_data(self, callback: CallbackQuery):
        """Обработка нажатия кнопки 'Собрать данные'"""
        session_id = callback.data.replace("collect_data_", "")
        await callback.answer("✅ Начинаю сбор данных...")

        if 'session_repo' not in self.repositories:
            await callback.message.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Показываем сообщение о начале сбора
        status_message = await callback.message.answer(
            "🔍 <b>Начинаю сбор данных с MPStats...</b>\n\n⏳ Это может занять 1-2 минуты..."
        )

        try:
            # Получаем сервис сбора данных
            data_collection_service = self.services.get('data_collection')

            if not data_collection_service:
                from app.services.data_collection_service import DataCollectionService
                from app.services.mpstats_scraper_service import MPStatsScraperService

                scraper_service = MPStatsScraperService(self.config)

                data_collection_service = DataCollectionService(
                    config=self.config,
                    scraper_service=scraper_service,
                    services={
                        'openai': self.services.get('openai'),
                        'prompt': self.services.get('prompt'),
                        'content': self.services.get('content')
                    }
                )
                self.services['data_collection'] = data_collection_service
                self.logger.info(
                    f"✅ DataCollectionService создан с сервисами: {list(data_collection_service.services.keys())}")

            # Получаем категорию по ID
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if not category:
                await status_message.edit_text("❌ Категория не найдена")
                return

            # Получаем описание категории
            category_description = ""
            if hasattr(category, 'description') and category.description:
                category_description = category.description
            elif hasattr(category, 'hidden_description') and category.hidden_description:
                category_description = category.hidden_description

            purposes = []
            if hasattr(session, 'purposes') and session.purposes:
                purposes = session.purposes

                # ПЕРЕВОДИМ НА РУССКИЙ ПЕРЕД ПЕРЕДАЧЕЙ В MPStats
                purpose_map = {
                    "wood": "под дерево", "with_pattern": "с рисунком", "kitchen": "кухня",
                    "tile": "плитка", "3d": "3D", "in_roll": "в рулоне",
                    "self_adhesive": "самоклеящиеся", "stone": "под камень", "bathroom": "ванная",
                    "bedroom": "спальня", "brick": "под кирпич", "marble": "под мрамор",
                    "living_room": "гостиная", "white": "белый"
                }

                translated_purposes = []
                for p in purposes:
                    translated = purpose_map.get(str(p).lower(), str(p))
                    translated_purposes.append(translated)

                purposes = translated_purposes

            # Запускаем сбор данных с GPT-фильтрацией
            result = await data_collection_service.collect_keywords_data(
                category=category.name,
                purpose=purposes,
                additional_params=session.additional_params or [],
                category_description=category_description
            )

            # В методе handle_collect_data, после получения filtered_keywords

            if result.get("status") == "success":
                filtered_keywords = result.get("keywords", [])

                # Убеждаемся, что это список, а не строка
                if isinstance(filtered_keywords, str):
                    # Если вдруг пришла строка, преобразуем
                    import json
                    try:
                        filtered_keywords = json.loads(filtered_keywords)
                    except:
                        filtered_keywords = [k.strip() for k in filtered_keywords.split(',')]

                # Убеждаемся, что purposes - это список
                if purposes and isinstance(purposes, str):
                    purposes = [purposes]
                elif not purposes:
                    purposes = []

                # Обновляем сессию
                session.keywords = filtered_keywords
                session.purposes = purposes  # Сохраняем как список
                session.current_step = "data_collected"

                session_repo.update(
                    session.id,
                    keywords=filtered_keywords,
                    purposes=purposes,
                    current_step="data_collected"
                )

                self.logger.info(f"✅ Сохранено keywords: {filtered_keywords} (тип: {type(filtered_keywords)})")
                self.logger.info(f"✅ Сохранено purposes: {purposes} (тип: {type(purposes)})")

                # Формируем сообщение с результатами
                message_text = (
                    f"✅ <b>Данные собраны и обработаны GPT!</b>\n\n"
                    f"📁 <b>Категория:</b> {result['category']}\n"
                )

                # Показываем назначения
                if result.get('purposes'):
                    purposes_list = result['purposes']
                    if isinstance(purposes_list, list) and purposes_list:
                        message_text += f"🎯 <b>Назначения:</b> {', '.join(purposes_list)}\n"
                    elif purposes_list:
                        message_text += f"🎯 <b>Назначение:</b> {purposes_list}\n"

                # Показываем отфильтрованные ключевые слова
                if filtered_keywords:
                    message_text += (
                        f"🔑 <b>Топ-{len(filtered_keywords)} ключевых слов (отфильтрованы GPT):</b>\n"
                    )
                    for i, keyword in enumerate(filtered_keywords, 1):
                        message_text += f"{i}. {keyword}\n"

                # Кнопки для продолжения
                builder = InlineKeyboardBuilder()
                builder.button(text="🎯 Меню генерации контента", callback_data=f"show_generation_menu_{session.id}")
                builder.button(
                    text="✏️ Ручная фильтрация ключей",
                    callback_data=f"manual_filter_{session.id}"
                )
                builder.button(text="📊 Показать все ключевые слова", callback_data=f"show_all_keywords_{session.id}")
                builder.button(text="↩️ Изменить параметры", callback_data="change_params")
                builder.adjust(1)

                await status_message.edit_text(message_text, reply_markup=builder.as_markup())

            else:
                # Ошибка
                await status_message.edit_text(
                    f"❌ <b>Ошибка при сборе данных:</b>\n{result.get('message', 'Неизвестная ошибка')}"
                )

        except Exception as e:
            await status_message.edit_text(f"❌ <b>Ошибка при сборе данных:</b>\n{str(e)[:200]}")
            self.logger.error(f"Ошибка сбора данных: {e}", exc_info=True)

    async def handle_show_generation_menu(self, callback: CallbackQuery):
        """Показать меню генерации контента"""
        session_id = callback.data.replace("show_generation_menu_", "")

        from app.bot.handlers.content_generation_handler import ContentGenerationHandler
        generation_handler = ContentGenerationHandler(self.config, self.services, self.repositories)

        await generation_handler.show_generation_menu(callback.message, session_id)
        await callback.answer()

    async def handle_back_to_menu(self, callback: CallbackQuery):
        """Возврат в главное меню"""
        await callback.answer()

        user_id = callback.from_user.id
        user_repo = self.repositories['user_repo']
        user = user_repo.get_by_telegram_id(user_id)

        from app.bot.handlers.start_handler import StartHandler
        start_handler = StartHandler(self.config, self.services, self.repositories)

        await start_handler.show_welcome_message(callback.message, user)

    def _get_category_display_name(self, category_id: str) -> str:
        """Получить отображаемое название категории"""
        categories_data = {
            "electronics": "📱 Электроника",
            "clothing": "👕 Одежда и обувь",
            "home": "🏠 Дом и сад",
            "beauty": "💄 Красота и здоровье"
        }
        return categories_data.get(category_id, "Неизвестная категория")

    async def handle_generate_title(self, callback: CallbackQuery):
        """Генерация заголовка"""
        user_id = callback.from_user.id

        if 'session_repo' not in self.repositories:
            await callback.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Здесь можно добавить логику генерации заголовка
        await callback.answer("🔄 Функция генерации заголовка в разработке")

    async def handle_regenerate_title(self, callback: CallbackQuery):
        """Перегенерация заголовка"""
        await self.handle_generate_title(callback)