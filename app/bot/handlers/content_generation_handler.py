# app/bot/handlers/content_generation_handler.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class ContentGenerationHandler(BaseMessageHandler):
    """Обработчик генерации контента для WB и Ozon"""

    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()
        self.logger = logging.getLogger(__name__)

    async def register(self, dp):
        """Регистрация обработчиков"""
        dp.include_router(self.router)

        # Кнопки генерации Wildberries
        self.router.callback_query.register(
            self.handle_generate_wb_title,
            F.data.startswith("generate_wb_title_")
        )
        self.router.callback_query.register(
            self.handle_generate_wb_short_desc,
            F.data.startswith("generate_wb_short_")
        )
        self.router.callback_query.register(
            self.handle_generate_wb_long_desc,
            F.data.startswith("generate_wb_long_")
        )

        # Кнопки генерации Ozon
        self.router.callback_query.register(
            self.handle_generate_ozon_title,
            F.data.startswith("generate_ozon_title_")
        )
        self.router.callback_query.register(
            self.handle_generate_ozon_desc,
            F.data.startswith("generate_ozon_desc_")
        )

        # Навигация
        self.router.callback_query.register(
            self.handle_back_to_generation_menu,
            F.data == "back_to_generation_menu"
        )

    async def show_generation_menu(self, message: Message, session_id: str):
        """Показать меню генерации контента"""
        builder = InlineKeyboardBuilder()

        # Кнопки Wildberries
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

        # Кнопки Ozon
        builder.button(
            text="🛍️ Название Ozon",
            callback_data=f"generate_ozon_title_{session_id}"
        )
        builder.button(
            text="📄 Описание Ozon",
            callback_data=f"generate_ozon_desc_{session_id}"
        )

        builder.button(
            text="↩️ Назад к результатам",
            callback_data="back_to_results"
        )

        builder.adjust(1)  # По одной кнопке в строке

        await message.edit_text(
            "🎯 <b>Выберите тип контента для генерации:</b>\n\n"
            "<b>Wildberries:</b>\n"
            "• Заголовок (до 60 символов)\n"
            "• Краткое описание (до 1000 символов)\n"
            "• Полное описание (до 2000 символов)\n\n"
            "<b>Ozon:</b>\n"
            "• SEO-название (120-160 символов)\n"
            "• SEO-описание (1500-3000 символов)\n\n"
            "Контент будет сгенерирован на основе собранных ключевых слов.",
            reply_markup=builder.as_markup()
        )

    async def _get_session_data(self, session_id: str):
        """Получить данные сессии и ключевые слова"""
        try:
            session_repo = self.repositories['session_repo']
            session = session_repo.get_by_id(session_id)

            if not session:
                return None, "❌ Сессия не найдена"

            # Получаем категорию
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if not category:
                return None, "❌ Категория не найдена"

            # Получаем ключевые слова из сессии или JSON
            keywords = session.keywords or []

            # Если нет ключевых слов в сессии, ищем в JSON файле
            if not keywords:
                import json
                import glob
                from pathlib import Path

                keywords_dir = Path(self.config.paths.keywords_dir)
                pattern = f"*{category.name}*enriched.json"
                json_files = list(keywords_dir.glob(pattern))

                if json_files:
                    with open(json_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        keywords = data.get("keywords", [])

            # Получаем назначения (поддержка старого и нового формата)
            purposes = []
            if hasattr(session, 'purposes') and session.purposes:
                purposes = session.purposes
            elif hasattr(session, 'purpose') and session.purpose:
                purposes = [session.purpose]

            # Получаем дополнительные параметры
            additional_params = session.additional_params or []

            return {
                'session': session,
                'category': category.name,
                'purposes': purposes,
                'additional_params': additional_params,
                'keywords': keywords
            }, None

        except Exception as e:
            self.logger.error(f"Ошибка получения данных сессии: {e}")
            return None, f"❌ Ошибка: {str(e)}"

    async def _generate_content(self, callback: CallbackQuery, session_id: str,
                                generation_type: str, marketplace: str):
        """Общий метод генерации контента"""
        try:
            await callback.answer(f"🔄 Генерирую {generation_type} для {marketplace}...")

            # Получаем данные
            data, error = await self._get_session_data(session_id)
            if error:
                await callback.message.answer(error)
                return

            # Получаем промпт
            prompt_service = self.services.get('prompt')
            if not prompt_service:
                await callback.message.answer("❌ Сервис промптов не найден")
                return

            # Выбираем нужный промпт
            if generation_type == "title" and marketplace == "wb":
                system_prompt, user_prompt = prompt_service.get_wb_title_prompt(
                    category=data['category'],
                    purposes=data['purposes'],
                    additional_params=data['additional_params'],
                    keywords=data['keywords']
                )
                result_type = "заголовок Wildberries"

            elif generation_type == "short_desc" and marketplace == "wb":
                system_prompt, user_prompt = prompt_service.get_wb_short_desc_prompt(
                    category=data['category'],
                    purposes=data['purposes'],
                    additional_params=data['additional_params'],
                    keywords=data['keywords']
                )
                result_type = "краткое описание Wildberries"

            elif generation_type == "long_desc" and marketplace == "wb":
                system_prompt, user_prompt = prompt_service.get_wb_long_desc_prompt(
                    category=data['category'],
                    purposes=data['purposes'],
                    additional_params=data['additional_params'],
                    keywords=data['keywords']
                )
                result_type = "полное описание Wildberries"

            elif generation_type == "title" and marketplace == "ozon":
                system_prompt, user_prompt = prompt_service.get_ozon_title_prompt(
                    category=data['category'],
                    purposes=data['purposes'],
                    additional_params=data['additional_params'],
                    keywords=data['keywords']
                )
                result_type = "SEO-название Ozon"

            elif generation_type == "desc" and marketplace == "ozon":
                system_prompt, user_prompt = prompt_service.get_ozon_desc_prompt(
                    category=data['category'],
                    purposes=data['purposes'],
                    additional_params=data['additional_params'],
                    keywords=data['keywords']
                )
                result_type = "SEO-описание Ozon"
            else:
                await callback.message.answer("❌ Неизвестный тип генерации")
                return

            # Генерируем контент через OpenAI
            openai_service = self.services.get('openai')
            if not openai_service:
                await callback.message.answer("❌ Сервис OpenAI не найден")
                return

            # Показываем сообщение о начале генерации
            status_msg = await callback.message.answer(f"🤖 <b>Генерирую {result_type}...</b>")

            # Устанавливаем max_tokens в зависимости от типа контента
            max_tokens = {
                "title": 100,
                "short_desc": 500,
                "long_desc": 1000,
                "desc": 1200
            }.get(generation_type, 500)

            content = await openai_service.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=0.7
            )

            if not content:
                await status_msg.edit_text(f"❌ Не удалось сгенерировать {result_type}")
                return

            # Показываем результат
            await status_msg.delete()

            builder = InlineKeyboardBuilder()
            builder.button(
                text="🔄 Сгенерировать заново",
                callback_data=callback.data
            )
            builder.button(
                text="📋 Скопировать",
                callback_data=f"copy_{hash(content)}"
            )
            builder.button(
                text="🎯 Другой тип контента",
                callback_data=f"back_to_generation_menu"
            )
            builder.adjust(1)

            # Форматируем вывод
            if generation_type == "title":
                display_text = f"<b>📝 {result_type}:</b>\n\n<code>{content}</code>\n\n"
                display_text += f"📏 <b>Длина:</b> {len(content)} символов\n"
                display_text += f"🔤 <b>Слов:</b> {len(content.split())}"
            else:
                display_text = f"<b>📄 {result_type}:</b>\n\n{content}\n\n"
                display_text += f"📏 <b>Длина:</b> {len(content)} символов"

            await callback.message.answer(display_text, reply_markup=builder.as_markup())

        except Exception as e:
            self.logger.error(f"Ошибка генерации контента: {e}")
            await callback.message.answer(f"❌ Ошибка генерации: {str(e)[:200]}")

    # Обработчики для каждой кнопки
    async def handle_generate_wb_title(self, callback: CallbackQuery):
        """Генерация заголовка Wildberries"""
        session_id = callback.data.replace("generate_wb_title_", "")
        await self._generate_content(callback, session_id, "title", "wb")

    async def handle_generate_wb_short_desc(self, callback: CallbackQuery):
        """Генерация краткого описания Wildberries"""
        session_id = callback.data.replace("generate_wb_short_", "")
        await self._generate_content(callback, session_id, "short_desc", "wb")

    async def handle_generate_wb_long_desc(self, callback: CallbackQuery):
        """Генерация полного описания Wildberries"""
        session_id = callback.data.replace("generate_wb_long_", "")
        await self._generate_content(callback, session_id, "long_desc", "wb")

    async def handle_generate_ozon_title(self, callback: CallbackQuery):
        """Генерация SEO-названия Ozon"""
        session_id = callback.data.replace("generate_ozon_title_", "")
        await self._generate_content(callback, session_id, "title", "ozon")

    async def handle_generate_ozon_desc(self, callback: CallbackQuery):
        """Генерация SEO-описания Ozon"""
        session_id = callback.data.replace("generate_ozon_desc_", "")
        await self._generate_content(callback, session_id, "desc", "ozon")

    async def handle_back_to_generation_menu(self, callback: CallbackQuery):
        """Возврат к меню генерации"""
        # Получаем session_id из предыдущего сообщения
        # Нужно будет доработать логику сохранения session_id
        await callback.answer("Функция в разработке")