import asyncio
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
        self.router.callback_query.register(self.handle_generate_title, F.data == "generate_title")
        self.router.callback_query.register(self.handle_regenerate_title, F.data == "regenerate_title")
        self.router.callback_query.register(self.handle_approve_title, F.data.startswith("approve_title_"))
        self.router.callback_query.register(self.handle_back_to_title, F.data == "back_to_title")  # Добавлено
        self.router.callback_query.register(self.handle_generate_short_desc, F.data.startswith("generate_short_"))
        self.router.callback_query.register(self.handle_generate_long_desc, F.data.startswith("generate_long_"))
        self.router.callback_query.register(self.handle_generate_both_desc, F.data.startswith("generate_both_"))
        self.router.callback_query.register(self.handle_approve_description, F.data.startswith("approve_desc_"))
        self.router.callback_query.register(self.handle_regenerate_description, F.data.startswith("regenerate_desc_"))
        self.router.message.register(self.show_generate_options, Command(commands=["generate"]))
        self.router.callback_query.register(self.handle_back_to_menu, F.data == "back_to_menu_from_generation")
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
            if not prompt_service:
                user_prompt = f"""
                Создай продающий заголовок для товара на маркетплейсе со следующими параметрами:

                Категория: {category.name}
                Назначение товара: {session.purpose}
                Дополнительные параметры: {', '.join(session.additional_params) if session.additional_params else 'нет'}

                Требования к заголовку:
                1. Максимально продающий и привлекательный
                2. Включает основные преимущества товара
                3. Соответствует категории "{category.name}"
                4. Оптимизирован для поиска на маркетплейсе
                5. Длина от 5 до 10 слов
                6. Не используй HTML теги
                7. Пиши на русском языке
                8. Не используй специальные символы "!, :, ^, )" и т.д.
                9. Дополнительные параметры должны привлекательно встраиваться в заголовок
                10. Ты создаешь заголовок в карточке товара на маркетплейсе
                """
                system_prompt = """
                Ты профессиональный копирайтер для маркетплейсов Wildberries и OZON.
                Создавай продающие, естественные заголовки для товаров.
                """
            else:
                user_prompt = prompt_service.get_title_prompt(
                    category.name,
                    session.purpose,
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
                generated_title = f"{category.name} {session.purpose} - {generated_title}"

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
            text += f"• <b>Назначение:</b> {session.purpose}\n"

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
                purpose=session.purpose
            )

        # Показываем варианты генерации описаний с кнопкой Назад
        builder = InlineKeyboardBuilder()
        builder.button(text="📋 Краткое описание", callback_data=f"generate_short_{session.id}")
        builder.button(text="📖 Подробное описание", callback_data=f"generate_long_{session.id}")
        builder.button(text="⚡ Оба описания", callback_data=f"generate_both_{session.id}")
        builder.button(text="↩️ Назад к заголовку", callback_data="back_to_title")  # Кнопка Назад
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
        text += f"• <b>Назначение:</b> {session.purpose}\n"

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

            prompt_service = self.services.get('prompt')
            if prompt_service:
                user_prompt = prompt_service.get_title_prompt(
                    category.name,
                    session.purpose,
                    session.additional_params if session.additional_params else []
                )
                system_prompt = prompt_service.get_system_prompt_for_title()
            else:
                user_prompt = f"""
                Создай продающий заголовок для товара на маркетплейсе со следующими параметрами:

                Категория: {category.name}
                Назначение товара: {session.purpose}
                Дополнительные параметры: {', '.join(session.additional_params) if session.additional_params else 'нет'}

                Требования к заголовку:
                1. Максимально продающий и привлекательный
                2. Включает основные преимущества товара
                3. Соответствует категории "{category.name}"
                4. Оптимизирован для поиска на маркетплейсе
                5. Длина от 5 до 10 слов
                6. Не используй HTML теги
                7. Пиши на русском языке
                8. Не используй специальные символы "!, :, ^, )" и т.д.
                9. Дополнительные параметры должны привлекательно встраиваться в заголовок
                10. Ты создаешь заголовок в карточке товара на маркетплейсе
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
            text += f"• <b>Назначение:</b> {session.purpose}\n"

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