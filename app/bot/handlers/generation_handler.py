# app/bot/handlers/generation_handler.py
import asyncio
import json
import logging
from aiogram.filters import Command
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler
from app.utils.logger import log
from app.utils.log_codes import LogCodes


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

        session_repo = self.repositories.get('session_repo')
        if not session_repo:
            await callback.message.answer("❌ Репозитории не инициализированы")
            return

        session = session_repo.get_by_id(session_id)
        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        status_message = await callback.message.answer(
            "🔍 <b>Начинаю сбор данных с MPStats...</b>\n\n⏳ Это может занять 1-2 минуты..."
        )

        try:
            # Берем сервис из self.services (создан при инициализации бота)
            data_collection_service = self.services.get('data_collection')

            # НЕ СОЗДАЕМ ЗАНОВО! Просто проверяем наличие
            if not data_collection_service:
                log.error(LogCodes.ERR_MPSTATS, error="DataCollectionService not initialized")
                await status_message.edit_text("❌ Сервис сбора данных не инициализирован")
                return

            category_repo = self.repositories.get('category_repo')
            category = category_repo.get_by_id(session.category_id)

            if not category:
                await status_message.edit_text("❌ Категория не найдена")
                return

            category_description = ""
            if hasattr(category, 'description') and category.description:
                category_description = category.description
            elif hasattr(category, 'hidden_description') and category.hidden_description:
                category_description = category.hidden_description

            purposes = []
            if hasattr(session, 'purposes') and session.purposes:
                purposes = session.purposes

            # Запускаем сбор данных
            result = await data_collection_service.collect_keywords_data(
                category=category.name,
                purpose=purposes,
                additional_params=session.additional_params or [],
                category_description=category_description
            )

            if result.get("status") == "success":
                filtered_keywords = result.get("keywords", [])

                if isinstance(filtered_keywords, str):
                    try:
                        filtered_keywords = json.loads(filtered_keywords)
                    except:
                        filtered_keywords = [k.strip() for k in filtered_keywords.split(',')]

                if purposes and isinstance(purposes, str):
                    purposes = [purposes]
                elif not purposes:
                    purposes = []

                session.keywords = filtered_keywords
                session.purposes = purposes
                session.current_step = "data_collected"

                session_repo.update(
                    session.id,
                    keywords=filtered_keywords,
                    purposes=purposes,
                    current_step="data_collected"
                )

                log.info(LogCodes.GEN_SAVE)

                message_text = (
                    f"✅ <b>Данные собраны и обработаны GPT!</b>\n\n"
                    f"📁 <b>Категория:</b> {result['category']}\n"
                )

                if result.get('purposes'):
                    purposes_list = result['purposes']
                    if isinstance(purposes_list, list) and purposes_list:
                        message_text += f"🎯 <b>Назначения:</b> {', '.join(purposes_list)}\n"

                if filtered_keywords:
                    message_text += f"🔑 <b>Топ-{len(filtered_keywords)} ключевых слов:</b>\n"
                    for i, keyword in enumerate(filtered_keywords[:10], 1):
                        message_text += f"{i}. {keyword}\n"

                builder = InlineKeyboardBuilder()
                builder.button(text="🎯 Меню генерации контента", callback_data=f"show_generation_menu_{session.id}")
                builder.button(
                    text="✏️ Ручная фильтрация ключей",
                    callback_data=f"manual_filter_{session.id}"
                )
                builder.button(text="↩️ Изменить параметры", callback_data="change_params")
                builder.adjust(1)

                await status_message.edit_text(message_text, reply_markup=builder.as_markup())
                log.info(LogCodes.SCR_SUCCESS)

            else:
                await status_message.edit_text(
                    f"❌ <b>Ошибка при сборе данных:</b>\n{result.get('message', 'Неизвестная ошибка')}"
                )
                log.error(LogCodes.SCR_ERROR, error=result.get('message', 'Unknown'))

        except Exception as e:
            await status_message.edit_text(f"❌ <b>Ошибка:</b>\n{str(e)[:200]}")
            log.error(LogCodes.ERR_HANDLER, handler="collect_data", error=str(e))

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

