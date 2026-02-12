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
        # self.router.callback_query.register(self.handle_generate_title, F.data == "generate_title")
        # self.router.callback_query.register(self.handle_regenerate_title, F.data == "regenerate_title")
        # self.router.callback_query.register(self.handle_approve_title, F.data.startswith("approve_title_"))
        # self.router.callback_query.register(self.handle_back_to_title, F.data == "back_to_title")
        # self.router.callback_query.register(self.handle_generate_short_desc, F.data.startswith("generate_short_"))
        # self.router.callback_query.register(self.handle_generate_long_desc, F.data.startswith("generate_long_"))
        # self.router.callback_query.register(self.handle_generate_both_desc, F.data.startswith("generate_both_"))
        # self.router.callback_query.register(self.handle_approve_description, F.data.startswith("approve_desc_"))
        # self.router.callback_query.register(self.handle_regenerate_description, F.data.startswith("regenerate_desc_"))
        # self.router.message.register(self.show_generate_options, Command(commands=["generate"]))
        self.router.callback_query.register(self.handle_back_to_menu, F.data == "back_to_menu_from_generation")
        self.router.callback_query.register(self.handle_collect_data, F.data.startswith("collect_data_"))
        self.router.callback_query.register(self.handle_show_generation_menu, F.data.startswith("show_generation_menu_"))

    # В class GenerationHandler добавьте:


    async def _get_generation_content(self, session) -> str:
        """Получить контент для генерации"""
        content = ""

        if session.current_step == "data_collected":
            content = "📊 <b>Данные собраны!</b>\n\n"
            content += f"🔑 Ключевых слов: {len(session.keywords or [])}\n"
            content += f"🎯 Назначения: {self._get_purposes_display_text(session)}\n"
            content += "\nЧто делаем дальше?"

        elif session.current_step == "title_generated":
            content = "📝 <b>Заголовок сгенерирован:</b>\n\n"
            content += f"<code>{session.generated_title}</code>\n\n"
            content += "Принимаем заголовок?"

        return content

    async def _get_generation_keyboard(self, session) -> InlineKeyboardBuilder:
        """Получить клавиатуру для генерации"""
        builder = InlineKeyboardBuilder()

        if session.current_step == "data_collected":
            builder.button(text="🚀 Сгенерировать заголовок", callback_data=f"generate_title_{session.id}")
            builder.button(text="🔍 Собрать другие данные", callback_data=f"collect_data_{session.id}")
            builder.button(text="↩️ Назад", callback_data="back_to_params")
            builder.button(text="❌ Отмена", callback_data="cancel_action")

        elif session.current_step == "title_generated":
            builder.button(text="✅ Принять", callback_data=f"approve_title_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data="regenerate_title")
            builder.button(text="📝 Изменить параметры", callback_data="change_params")
            builder.button(text="❌ Отмена", callback_data="cancel_action")

        builder.adjust(2)
        return builder

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
                # Создаем сервис при необходимости, передавая другие сервисы
                from app.services.data_collection_service import DataCollectionService
                from app.services.mpstats_scraper_service import MPStatsScraperService

                scraper_service = MPStatsScraperService(self.config)

                # Передаем необходимые сервисы
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
                # purpose=session.purposes if hasattr(session, 'purposes') and session.purposes else [],
                purpose=purposes,
                additional_params=session.additional_params or [],
                category_description=category_description
            )

            if result.get("status") == "success":
                # Обновляем сессию с отфильтрованными ключевыми словами
                filtered_keywords = result.get("keywords", [])
                session.keywords = filtered_keywords
                session.current_step = "data_collected"

                session_repo.update(
                    session.id,
                    keywords=filtered_keywords,
                    current_step="data_collected"
                )

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
                # builder.button(text="🚀 Сгенерировать заголовок", callback_data=f"generate_title_advanced_{session.id}")
                builder.button(text="🎯 Меню генерации контента", callback_data=f"show_generation_menu_{session.id}")
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

        # Используем ContentGenerationHandler
        from app.bot.handlers.content_generation_handler import ContentGenerationHandler
        generation_handler = ContentGenerationHandler(self.config, self.services, self.repositories)

        await generation_handler.show_generation_menu(callback.message, session_id)
        await callback.answer()

    async def handle_show_all_keywords(self, callback: CallbackQuery):
        """Показать все ключевые слова (оригинальные и отфильтрованные)"""
        session_id = callback.data.replace("show_all_keywords_", "")

        if 'session_repo' not in self.repositories:
            await callback.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Загружаем JSON файл
        try:
            import glob
            import os
            from pathlib import Path

            # Ищем JSON файл для этой сессии
            keywords_dir = Path(self.config.paths.keywords_dir)
            pattern = f"*{session.category_id}*enriched.json"
            json_files = list(keywords_dir.glob(pattern))

            if json_files:
                json_file = json_files[0]
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                all_keywords = data.get("all_keywords", [])
                filtered_keywords = data.get("keywords", [])

                message_text = f"📊 <b>Все ключевые слова:</b>\n\n"
                message_text += f"<b>Отфильтровано GPT ({len(filtered_keywords)}):</b>\n"
                for kw in filtered_keywords:
                    message_text += f"✅ {kw}\n"

                message_text += f"\n<b>Всего собрано ({len(all_keywords)}):</b>\n"
                # Показываем первые 30 из всех
                for i, kw in enumerate(all_keywords[:30], 1):
                    is_filtered = kw in filtered_keywords
                    icon = "✅" if is_filtered else "🔸"
                    message_text += f"{icon} {kw}\n"

                if len(all_keywords) > 30:
                    message_text += f"\n... и еще {len(all_keywords) - 30} ключевых слов"

                await callback.message.answer(message_text)
            else:
                await callback.answer("❌ JSON файл не найден")

        except Exception as e:
            await callback.answer(f"❌ Ошибка: {str(e)[:50]}")


    async def _generate_title_simple(self, callback: CallbackQuery, session):
        """Простая генерация заголовка через OpenAI"""
        user_id = callback.from_user.id

        try:
            await callback.answer("🚀 Начинаю генерацию...")
        except:
            pass

        msg = await callback.message.answer("🚀 <b>Генерирую заголовок...</b>")

        try:
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if not category:
                await msg.edit_text("❌ Категория не найдена")
                return

            if 'openai' not in self.services:
                await msg.edit_text("❌ Сервис OpenAI не инициализирован")
                return

            # Используем PromptService для получения промптов
            prompt_service = self.services.get('prompt')

            # ИЗМЕНЕНО: обрабатываем как массив purposes
            purposes_text = ""
            if hasattr(session, 'purposes') and session.purposes:
                if isinstance(session.purposes, list):
                    purposes_text = ", ".join(session.purposes)
                else:
                    purposes_text = str(session.purposes)
            elif hasattr(session, 'purpose'):
                purposes_text = session.purpose

            if not prompt_service:
                await msg.edit_text("❌ fakdfjalkfj")
                return
            else:
                user_prompt = prompt_service.get_title_prompt(
                    category.name,
                    purposes_text,
                    session.additional_params if session.additional_params else []
                )
                system_prompt = prompt_service.get_system_prompt_for_title()

            openai_service = self.services['openai']

            await msg.edit_text("🚀 <b>Генерирую заголовок с помощью OpenAI...</b>")

            generated_title = await openai_service.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=150,
                temperature=0.7
            )

            if not generated_title:
                await msg.edit_text("❌ Не удалось сгенерировать заголовок")
                return

            generated_title = generated_title.strip()
            generated_title = generated_title.strip('"').strip("'").strip()

            if generated_title.startswith("Заголовок:"):
                generated_title = generated_title.replace("Заголовок:", "").strip()

            if len(generated_title) < 10:
                generated_title = f"{category.name} {purposes_text} - {generated_title}"

            self.logger.info(f"✅ Сгенерирован заголовок: {generated_title}")

            session_repo = self.repositories['session_repo']
            session.generated_title = generated_title
            session.current_step = "title_generated"

            session_repo.update(
                session.id,
                generated_title=generated_title,
                current_step="title_generated"
            )

            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Принять", callback_data=f"approve_title_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data="regenerate_title")
            builder.button(text="📝 Изменить параметры", callback_data="change_params")
            builder.adjust(1)

            text = f"📝 <b>Предлагаю заголовок:</b>\n\n"
            text += f"<code>{generated_title}</code>\n\n"
            text += f"📋 <b>Параметры товара:</b>\n"
            text += f"• <b>Категория:</b> {category.name}\n"
            text += f"• <b>Назначения:</b> {purposes_text}\n"  # ИЗМЕНЕНО

            if session.additional_params:
                text += f"• <b>Доп. параметры:</b> {', '.join(session.additional_params)}\n"

            text += f"\n🔸 <i>Заголовок сгенерирован на основе указанных параметров</i>"

            try:
                await msg.delete()
            except:
                pass

            await callback.message.answer(text, reply_markup=builder.as_markup())

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации: {e}", exc_info=True)

            try:
                await msg.edit_text(f"❌ <b>Ошибка генерации:</b> {str(e)[:200]}")
            except:
                await callback.message.answer(f"❌ <b>Ошибка генерации:</b> {str(e)[:200]}")

            builder = InlineKeyboardBuilder()
            builder.button(text="📝 Изменить параметры", callback_data="change_params")
            builder.button(text="🔄 Попробовать еще раз", callback_data="generate_title")
            builder.adjust(1)

            await callback.message.answer(
                "Попробуйте изменить параметры или попробовать еще раз:",
                reply_markup=builder.as_markup()
            )

    async def handle_approve_title(self, callback: CallbackQuery):
        """Подтверждение заголовка с кнопкой Назад"""
        session_id = callback.data.replace("approve_title_", "")

        if 'session_repo' not in self.repositories:
            await callback.answer("❌ Репозиторий сессий не инициализирован")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # ИЗМЕНЕНО: получаем назначения
        purposes_text = ""
        if hasattr(session, 'purposes') and session.purposes:
            if isinstance(session.purposes, list):
                purposes_text = ", ".join(session.purposes)
            else:
                purposes_text = str(session.purposes)
        elif hasattr(session, 'purpose'):
            purposes_text = session.purpose

        # Обновляем шаг сессии
        session.current_step = "title_approved"
        session_repo.update(session.id, current_step="title_approved")

        # Сохраняем в таблице generated_content
        if 'content_repo' in self.repositories:
            content_repo = self.repositories['content_repo']
            content_repo.create(
                session_id=session.id,
                user_id=session.user_id,
                title=session.generated_title,
                short_description="",
                long_description="",
                keywords=session.keywords if session.keywords else [],
                category_id=session.category_id,
                purpose=purposes_text  # ИЗМЕНЕНО
            )

        # Показываем варианты генерации описаний с кнопкой Назад
        builder = InlineKeyboardBuilder()
        builder.button(text="📋 Краткое описание", callback_data=f"generate_short_{session.id}")
        builder.button(text="📖 Подробное описание", callback_data=f"generate_long_{session.id}")
        builder.button(text="⚡ Оба описания", callback_data=f"generate_both_{session.id}")
        builder.button(text="↩️ Назад к заголовку", callback_data="back_to_title")
        builder.adjust(1)

        await callback.message.edit_text(
            f"✅ <b>Заголовок принят и сохранен!</b>\n\n"
            f"<code>{session.generated_title}</code>\n\n"
            "📄 <b>Выберите тип описания:</b>",
            reply_markup=builder.as_markup()
        )
        await callback.answer()

    async def handle_back_to_title(self, callback: CallbackQuery):
        """Возврат к просмотру заголовка"""
        user_id = callback.from_user.id

        if 'session_repo' not in self.repositories:
            await callback.answer("❌ Репозиторий сессий не инициализирован")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session or not session.generated_title:
            await callback.answer("❌ Заголовок не найден")
            return

        category_repo = self.repositories['category_repo']
        category = category_repo.get_by_id(session.category_id)

        # ИЗМЕНЕНО: получаем назначения
        purposes_text = ""
        if hasattr(session, 'purposes') and session.purposes:
            if isinstance(session.purposes, list):
                purposes_text = ", ".join(session.purposes)
            else:
                purposes_text = str(session.purposes)
        elif hasattr(session, 'purpose'):
            purposes_text = session.purpose

        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Принять", callback_data=f"approve_title_{session.id}")
        builder.button(text="🔄 Перегенерировать", callback_data="regenerate_title")
        builder.button(text="📝 Изменить параметры", callback_data="change_params")
        builder.adjust(1)

        text = f"📝 <b>Предлагаю заголовок:</b>\n\n"
        text += f"<code>{session.generated_title}</code>\n\n"
        text += f"📋 <b>Параметры товара:</b>\n"
        if category:
            text += f"• <b>Категория:</b> {category.name}\n"
        text += f"• <b>Назначения:</b> {purposes_text}\n"  # ИЗМЕНЕНО

        if session.additional_params:
            text += f"• <b>Доп. параметры:</b> {', '.join(session.additional_params)}\n"

        text += f"\n🔸 <i>Заголовок сгенерирован на основе указанных параметров</i>"

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()

    async def handle_generate_both_desc(self, callback: CallbackQuery):
        """Генерация обоих описаний с кнопками Принять и Перегенерировать"""
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

            # Генерируем краткое описание
            short_desc = await content_service.generate_description_workflow(
                session.generated_title, [], "short", category.name if category else "товар", {}
            )

            # Генерируем подробное описание
            long_desc = await content_service.generate_description_workflow(
                session.generated_title, [], "long", category.name if category else "товар", {}
            )

            # Сохраняем в сессии
            session.short_description = short_desc
            session.long_description = long_desc
            session.current_step = "descriptions_generated"

            session_repo.update(
                session.id,
                short_description=short_desc,
                long_description=long_desc,
                current_step="descriptions_generated"
            )

            # Сохраняем в таблице generated_content (обновляем существующую запись)
            if 'content_repo' in self.repositories:
                content_repo = self.repositories['content_repo']
                # Ищем существующую запись
                existing_content = content_repo.get_session_content(session.id)
                if existing_content:
                    # Обновляем
                    existing_content.short_description = short_desc
                    existing_content.long_description = long_desc
                    with content_repo.get_session() as db_session:
                        db_session.commit()
                else:
                    # Создаем новую
                    content_repo.create(
                        session_id=session.id,
                        user_id=session.user_id,
                        title=session.generated_title,
                        short_description=short_desc,
                        long_description=long_desc,
                        keywords=session.keywords if session.keywords else [],
                        category_id=session.category_id,
                        purpose=session.purpose
                    )

            # Добавляем кнопки Принять и Перегенерировать
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Принять описания", callback_data=f"approve_desc_both_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data=f"regenerate_desc_both_{session.id}")
            builder.button(text="🏠 Меню", callback_data="back_to_menu_from_generation")
            builder.adjust(1)

            await callback.message.edit_text(
                f"✅ <b>Оба описания сгенерированы!</b>\n\n"
                f"📝 <b>Заголовок:</b>\n<code>{session.generated_title}</code>\n\n"
                f"📋 <b>Краткое описание:</b>\n{short_desc}\n\n"
                f"📖 <b>Подробное описание:</b>\n{long_desc}\n\n"
                f"💾 <b>Контент готов для сохранения</b>",
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации описаний: {e}", exc_info=True)
            await callback.message.edit_text(f"❌ <b>Ошибка генерации:</b> {str(e)}")

        await callback.answer()

    async def handle_generate_short_desc(self, callback: CallbackQuery):
        """Генерация краткого описания с кнопками Принять и Перегенерировать"""
        session_id = callback.data.replace("generate_short_", "")
        await self._generate_single_description(callback, session_id, "short")

    async def handle_generate_long_desc(self, callback: CallbackQuery):
        """Генерация подробного описания с кнопками Принять и Перегенерировать"""
        session_id = callback.data.replace("generate_long_", "")
        await self._generate_single_description(callback, session_id, "long")

    async def _generate_single_description(self, callback: CallbackQuery, session_id: str, desc_type: str):
        """Генерация одного описания с кнопками"""
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

            description = await content_service.generate_description_workflow(
                session.generated_title, [], desc_type, category.name if category else "товар", {}
            )

            # Сохраняем в сессии
            if desc_type == "short":
                session.short_description = description
            else:
                session.long_description = description

            session.current_step = f"{desc_type}_description_generated"

            session_repo.update(
                session.id,
                **{f"{desc_type}_description": description, "current_step": f"{desc_type}_description_generated"}
            )

            # Создаем кнопки
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Принять", callback_data=f"approve_desc_{desc_type}_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data=f"regenerate_desc_{desc_type}_{session.id}")

            if desc_type == "short":
                builder.button(text="📖 Сгенерировать подробное", callback_data=f"generate_long_{session.id}")
            else:
                builder.button(text="📋 Сгенерировать краткое", callback_data=f"generate_short_{session.id}")

            builder.button(text="⚡ Оба описания", callback_data=f"generate_both_{session.id}")
            builder.adjust(1)

            await callback.message.edit_text(
                f"✅ <b>{type_name.title()} описание:</b>\n\n{description}",
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации {type_name} описания: {e}", exc_info=True)
            await callback.message.edit_text(f"❌ <b>Ошибка генерации:</b> {str(e)}")

        await callback.answer()

    async def handle_approve_description(self, callback: CallbackQuery):
        """Принятие описания"""
        data_parts = callback.data.replace("approve_desc_", "").split("_")

        if len(data_parts) < 2:
            await callback.answer("❌ Ошибка данных")
            return

        desc_type = data_parts[0]
        session_id = data_parts[1] if len(data_parts) > 1 else "_".join(data_parts[1:])

        if 'session_repo' not in self.repositories:
            await callback.answer("❌ Репозиторий сессий не инициализирован")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_by_id(session_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        type_name = "краткое" if desc_type == "short" else "подробное" if desc_type == "long" else "оба"

        # Обновляем сессию
        session.current_step = f"{desc_type}_description_approved"
        session_repo.update(session.id, current_step=f"{desc_type}_description_approved")

        # Сохраняем в таблице generated_content если еще не сохранено
        if 'content_repo' in self.repositories and (desc_type == "both" or desc_type == "long"):
            content_repo = self.repositories['content_repo']
            existing_content = content_repo.get_session_content(session.id)

            if not existing_content:
                content_repo.create(
                    session_id=session.id,
                    user_id=session.user_id,
                    title=session.generated_title,
                    short_description=session.short_description,
                    long_description=session.long_description,
                    keywords=session.keywords if session.keywords else [],
                    category_id=session.category_id,
                    purpose=session.purpose
                )

        builder = InlineKeyboardBuilder()
        builder.button(text="🏠 Меню", callback_data="back_to_menu_from_generation")
        builder.adjust(1)

        await callback.message.edit_text(
            f"✅ <b>{type_name.title()} описание принято и сохранено!</b>\n\n"
            f"📝 <b>Заголовок:</b>\n<code>{session.generated_title}</code>\n\n"
            f"💾 <b>Контент сохранен в истории. Вы можете посмотреть его в /session</b>",
            reply_markup=builder.as_markup()
        )
        await callback.answer()

    async def handle_regenerate_description(self, callback: CallbackQuery):
        """Перегенерация описания"""
        data_parts = callback.data.replace("regenerate_desc_", "").split("_")

        if len(data_parts) < 2:
            await callback.answer("❌ Ошибка данных")
            return

        desc_type = data_parts[0]
        session_id = data_parts[1] if len(data_parts) > 1 else "_".join(data_parts[1:])

        if desc_type == "both":
            await self.handle_generate_both_desc(callback)
        elif desc_type == "short":
            await self.handle_generate_short_desc(callback)
        elif desc_type == "long":
            await self.handle_generate_long_desc(callback)

    async def handle_back_to_menu(self, callback: CallbackQuery):
        """Возврат в главное меню"""
        await callback.answer()

        user_id = callback.from_user.id
        user_repo = self.repositories['user_repo']
        user = user_repo.get_by_telegram_id(user_id)

        from app.bot.handlers.start_handler import StartHandler
        start_handler = StartHandler(self.config, self.services, self.repositories)

        await start_handler.show_welcome_message(callback.message, user)

    async def show_generate_options(self, message: Message):
        """Показать опции генерации"""
        user_id = message.from_user.id

        if 'session_repo' not in self.repositories:
            await message.answer("❌ Репозиторий сессий не инициализирован")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await message.answer(
                "⚠️ Сначала завершите настройку товара:\n"
                "Используйте команду /categories"
            )
            return

        if not hasattr(session, 'generation_mode') or session.generation_mode not in ['simple', 'advanced']:
            await message.answer(
                "⚠️ Сначала выберите способ генерации!\n\n"
                "Завершите настройку параметров и выберите способ генерации."
            )
            return

        category_name = self._get_category_display_name(session.category_id)
        generation_mode = session.generation_mode

        if generation_mode == 'simple':
            await message.answer(f"🚀 <b>Начинаю простую генерацию для категории:</b> {category_name}")
            await asyncio.sleep(0.5)
            await self._generate_title_simple_from_message(message, session)
        else:
            await message.answer(
                "🤖 <b>Продвинутая генерация временно недоступна</b>\n\n"
                "Переключаюсь на простую генерацию..."
            )
            session.generation_mode = 'simple'
            session_repo.update(session.id, generation_mode='simple')
            await self._generate_title_simple_from_message(message, session)

    async def _generate_title_simple_from_message(self, message: Message, session):
        """Простая генерация заголовка из сообщения"""
        user_id = message.from_user.id

        await message.answer("🚀 <b>Генерирую заголовок...</b>")

        try:
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if not category:
                await message.answer("❌ Категория не найдена")
                return

            if 'openai' not in self.services:
                await message.answer("❌ Сервис OpenAI не инициализирован")
                return

            # ИЗМЕНЕНО: получаем назначения
            purposes_text = ""
            if hasattr(session, 'purposes') and session.purposes:
                if isinstance(session.purposes, list):
                    purposes_text = ", ".join(session.purposes)
                else:
                    purposes_text = str(session.purposes)
            elif hasattr(session, 'purpose'):
                purposes_text = session.purpose

            prompt_service = self.services.get('prompt')
            if prompt_service:
                user_prompt = prompt_service.get_title_prompt(
                    category.name,
                    purposes_text,
                    session.additional_params if session.additional_params else []
                )
                system_prompt = prompt_service.get_system_prompt_for_title()
            else:
                user_prompt = f"""
                Создай продающий заголовок для товара на маркетплейсе со следующими параметрами:

                Категория: {category.name}
                Назначения товара: {purposes_text}
                Дополнительные параметры: {', '.join(session.additional_params) if session.additional_params else 'нет'}

                Требования к заголовку:
                1. Максимально продающий и привлекательный
                2. Включает основные преимущества товара
                3. Соответствует категории "{category.name}"
                4. Учитывает все назначения: {purposes_text}
                5. Оптимизирован для поиска на маркетплейсе
                6. Длина от 5 до 10 слов
                7. Не используй HTML теги
                8. Пиши на русском языке
                9. Не используй специальные символы "!, :, ^, )" и т.д.
                10. Дополнительные параметры должны привлекательно встраиваться в заголовок
                11. Ты создаешь заголовок в карточке товара на маркетплейсе
                """
                system_prompt = """
                Ты профессиональный копирайтер для маркетплейсов Wildberries и OZON.
                Создавай продающие, естественные заголовки для товаров.
                """

            openai_service = self.services['openai']

            generated_title = await openai_service.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=150,
                temperature=0.7
            )

            if not generated_title:
                await message.answer("❌ Не удалось сгенерировать заголовок")
                return

            generated_title = generated_title.strip()
            generated_title = generated_title.strip('"').strip("'").strip()

            if generated_title.startswith("Заголовок:"):
                generated_title = generated_title.replace("Заголовок:", "").strip()

            session_repo = self.repositories['session_repo']
            session.generated_title = generated_title
            session.current_step = "title_generated"

            session_repo.update(
                session.id,
                generated_title=generated_title,
                current_step="title_generated"
            )

            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Принять", callback_data=f"approve_title_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data="regenerate_title")
            builder.button(text="📝 Изменить параметры", callback_data="change_params")
            builder.adjust(1)

            text = f"📝 <b>Предлагаю заголовок:</b>\n\n"
            text += f"<code>{generated_title}</code>\n\n"
            text += f"📋 <b>Параметры товара:</b>\n"
            text += f"• <b>Категория:</b> {category.name}\n"
            text += f"• <b>Назначения:</b> {purposes_text}\n"  # ИЗМЕНЕНО

            if session.additional_params:
                text += f"• <b>Доп. параметры:</b> {', '.join(session.additional_params)}\n"

            text += f"\n🔸 <i>Заголовок сгенерирован на основе указанных параметров</i>"

            await message.answer(text, reply_markup=builder.as_markup())

        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации: {e}", exc_info=True)

            builder = InlineKeyboardBuilder()
            builder.button(text="📝 Изменить параметры", callback_data="change_params")
            builder.button(text="🔄 Попробовать еще раз", callback_data="generate_title")
            builder.adjust(1)

            await message.answer(
                f"❌ <b>Ошибка генерации:</b> {str(e)[:200]}\n\n"
                "Попробуйте изменить параметры или попробовать еще раз:",
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

        await self._generate_title_simple(callback, session)

    async def handle_regenerate_title(self, callback: CallbackQuery):
        """Перегенерация заголовка"""
        await self.handle_generate_title(callback)