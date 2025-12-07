
import asyncio
import logging
import os
import json
from pathlib import Path
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
        # Путь для сохранения файлов
        self.downloads_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'utils',
            'downloads',
            'mpstats'
        )
        os.makedirs(self.downloads_dir, exist_ok=True)

        # Путь для сохранения JSON файлов с ключевыми словами
        self.keywords_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'utils',
            'keywords'
        )
        os.makedirs(self.keywords_dir, exist_ok=True)

    async def register(self, dp):
        dp.include_router(self.router)
        self.router.callback_query.register(self.handle_generate_title, F.data == "generate_title")
        self.router.callback_query.register(self.handle_regenerate_title, F.data == "regenerate_title")
        self.router.callback_query.register(self.handle_approve_title, F.data.startswith("approve_title_"))
        self.router.callback_query.register(self.handle_generate_short_desc, F.data.startswith("generate_short_"))
        self.router.callback_query.register(self.handle_generate_long_desc, F.data.startswith("generate_long_"))
        self.router.callback_query.register(self.handle_generate_both_desc, F.data.startswith("generate_both_"))
        self.router.message.register(self.show_generate_options, Command(commands=["generate"]))
        self.router.callback_query.register(self.handle_collect_data, F.data == "collect_data")

    async def show_generate_options(self, message: Message):
        """Показать опции генерации в зависимости от выбранного режима"""
        user_id = message.from_user.id
        self.logger.info(f"=== ВЫЗВАН /generate для пользователя {user_id} ===")

        # Проверяем наличие репозитория
        if 'session_repo' not in self.repositories:
            self.logger.error("❌ session_repo не найден в repositories!")
            await message.answer("❌ Ошибка: репозиторий сессий не инициализирован")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await message.answer(
                "⚠️ Сначала завершите настройку товара:\n"
                "1. <code>/categories</code> - выбрать категорию и назначение\n"
                "2. Укажите дополнительные параметры\n"
                "3. Выберите способ генерации\n"
                "4. Затем используйте <code>/generate</code>"
            )
            return

        # Проверяем выбран ли способ генерации
        if not hasattr(session, 'generation_mode') or session.generation_mode not in ['simple', 'advanced']:
            await message.answer(
                "⚠️ Сначала выберите способ генерации!\n\n"
                "Завершите настройку параметров и выберите способ генерации."
            )
            return

        # Получаем название категории
        category_name = self._get_category_display_name(session.category_id)
        generation_mode = session.generation_mode

        if generation_mode == 'advanced':
            # Продвинутая генерация - создаем тестовые данные
            await message.answer(f"🔍 <b>Создаю тестовые данные для категории:</b> {category_name}")

            try:
                # Создаем тестовые данные
                test_file_path = await self._create_test_data({
                    'category': session.category_id,
                    'purpose': session.purpose,
                    'additional_params': session.additional_params if session.additional_params else [],
                    'user_id': user_id,
                    'session_id': session.id
                })

                if test_file_path and os.path.exists(test_file_path):
                    # Обновляем шаг сессии
                    session.current_step = "data_scraped"
                    session_repo.update(
                        session.id,
                        current_step="data_scraped"
                    )

                    # Загружаем ключевые слова для отображения
                    keywords = await self._load_keywords_from_json(test_file_path)
                    keywords_preview = ', '.join(keywords[:5]) + '...' if keywords else 'нет данных'

                    # Показываем результат и кнопку генерации
                    builder = InlineKeyboardBuilder()
                    builder.button(text="🤖 Сгенерировать заголовок", callback_data="generate_title")

                    await message.answer(
                        f"✅ <b>Тестовые данные успешно созданы!</b>\n\n"
                        f"📊 <b>Режим:</b> 🤖 Продвинутая генерация\n"
                        f"🔑 <b>Ключевые слова:</b> {len(keywords)} шт.\n"
                        f"<i>Примеры: {keywords_preview}</i>\n\n"
                        "Нажмите кнопку ниже чтобы начать генерацию контента:",
                        reply_markup=builder.as_markup()
                    )
                else:
                    await message.answer(
                        "❌ <b>Не удалось создать тестовые данные</b>\n\n"
                        "Переключаюсь на простую генерацию..."
                    )
                    # Переключаемся на простую генерацию
                    session.generation_mode = 'simple'
                    session_repo.update(session.id, generation_mode='simple')
                    await self._show_simple_generation_ui(message, session)

            except Exception as e:
                self.logger.error(f"❌ Ошибка при создании тестовых данных: {e}", exc_info=True)
                await message.answer(
                    f"❌ <b>Ошибка при создании тестовых данных:</b>\n{str(e)[:200]}\n\n"
                    "Переключаюсь на простую генерацию..."
                )
                # Переключаемся на простую генерацию
                session.generation_mode = 'simple'
                session_repo.update(session.id, generation_mode='simple')
                await self._show_simple_generation_ui(message, session)

        else:
            # Простая генерация - НЕ создаем тестовые данные, сразу переходим к генерации
            await message.answer(f"🚀 <b>Начинаю простую генерацию для категории:</b> {category_name}")

            # Сразу вызываем генерацию заголовка
            await self._generate_title_simple(session)

    async def _show_simple_generation_ui(self, message: Message, session):
        """Показать интерфейс для простой генерации"""
        # Получаем название категории
        category_name = self._get_category_display_name(session.category_id)

        # Показываем информацию и кнопку генерации
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Сгенерировать заголовок", callback_data="generate_title")

        await message.answer(
            f"🚀 <b>Простая генерация контента</b>\n\n"
            f"📊 <b>Параметры:</b>\n"
            f"• <b>Категория:</b> {category_name}\n"
            f"• <b>Назначение:</b> {session.purpose}\n"
            f"• <b>Доп. параметры:</b> {', '.join(session.additional_params) if session.additional_params else 'нет'}\n\n"
            "Нажмите кнопку ниже чтобы сгенерировать контент на основе OpenAI:",
            reply_markup=builder.as_markup()
        )

    # app/bot/handlers/generation_handler.py
    # Обновляем метод для работы без сохранения пути

    async def _create_test_data(self, scraper_params):
        """
        Создает тестовые данные используя data_gen_service и keywords_processor

        Args:
            scraper_params: Параметры для создания данных

        Returns:
            Путь к созданному JSON файлу или None
        """
        try:
            # 1. Используем data_gen_service для создания тестового XLSX файла
            category = scraper_params.get('category', 'unknown')
            self.logger.info(f"Создание тестового XLSX файла для категории: {category}")

            if 'data_gen' not in self.services:
                self.logger.error("❌ data_gen service не найден в services!")
                return None

            data_gen_service = self.services['data_gen']
            xlsx_file_path = data_gen_service.create_test_xlsx_file(category)

            if not xlsx_file_path or not os.path.exists(xlsx_file_path):
                self.logger.error(f"Не удалось создать XLSX файл: {xlsx_file_path}")
                return None

            self.logger.info(f"Тестовый XLSX файл создан: {xlsx_file_path}")

            # 2. Создаем JSON файл с помощью keywords_processor
            if 'keywords_processor' not in self.services:
                self.logger.error("❌ keywords_processor service не найден в services!")
                return None

            processor = self.services['keywords_processor']

            # Создаем обогащенный JSON
            json_file_path = processor.create_enriched_json(
                excel_path=xlsx_file_path,
                category=scraper_params.get('category', 'unknown'),
                purpose=scraper_params.get('purpose', 'unknown'),
                additional_params=scraper_params.get('additional_params', [])
            )

            # 3. Удаляем временный XLSX файл
            try:
                if os.path.exists(xlsx_file_path):
                    os.remove(xlsx_file_path)
                    self.logger.info(f"Временный XLSX файл удален: {xlsx_file_path}")
            except Exception as e:
                self.logger.warning(f"Не удалось удалить временный XLSX файл: {e}")

            return json_file_path

        except Exception as e:
            self.logger.error(f"Ошибка в _create_test_data: {e}", exc_info=True)
            return None

    async def _process_xlsx_to_json(self, xlsx_file_path, scraper_params):
        """
        Обрабатывает XLSX файл через keywords_processor для создания JSON

        Args:
            xlsx_file_path: Путь к XLSX файлу
            scraper_params: Параметры для включения в JSON

        Returns:
            Путь к созданному JSON файлу
        """
        try:
            # Проверяем наличие keywords_processor
            if 'keywords_processor' not in self.services:
                self.logger.error("❌ keywords_processor service не найден в services!")
                return None

            processor = self.services['keywords_processor']

            # Создаем обогащенный JSON
            enriched_json_path = processor.create_enriched_json(
                excel_path=xlsx_file_path,
                category=scraper_params.get('category', 'unknown'),
                purpose=scraper_params.get('purpose', 'unknown'),
                additional_params=scraper_params.get('additional_params', [])
            )

            if not enriched_json_path or not os.path.exists(enriched_json_path):
                self.logger.error(f"Не удалось создать обогащенный JSON файл")
                return None

            self.logger.info(f"Обогащенный JSON файл создан: {enriched_json_path}")

            return enriched_json_path

        except Exception as e:
            self.logger.error(f"Ошибка в _process_xlsx_to_json: {e}", exc_info=True)
            return None

    def _get_category_display_name(self, category_id: str) -> str:
        """Получить отображаемое название категории"""
        categories_data = {
            "electronics": "📱 Электроника",
            "clothing": "👕 Одежда и обувь",
            "home": "🏠 Дом и сад",
            "beauty": "💄 Красота и здоровье"
        }
        return categories_data.get(category_id, "Неизвестная категория")

    # app/bot/handlers/generation_handler.py
    async def _load_keywords_from_json(self, json_file_path):
        """
        Загружает ключевые слова из JSON файла

        Args:
            json_file_path: Путь к JSON файлу

        Returns:
            Список ключевых слов
        """
        try:
            if not os.path.exists(json_file_path):
                self.logger.error(f"JSON файл не найден: {json_file_path}")
                return []

            # Проверяем наличие keywords_processor
            if 'keywords_processor' in self.services:
                processor = self.services['keywords_processor']
                return processor.load_keywords_from_json(json_file_path)

            # Альтернативный способ загрузки
            import json
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Пытаемся получить ключевые слова из разных форматов
            if 'keywords' in data:
                return data['keywords']
            elif 'words' in data:
                return data['words']
            else:
                self.logger.warning(f"Ключевые слова не найдены в JSON: {json_file_path}")
                return []

        except Exception as e:
            self.logger.error(f"Ошибка загрузки ключевых слов: {e}")
            return []

    # Обновляем метод handle_generate_title для использования ключевых слов из JSON
    async def handle_generate_title(self, callback: CallbackQuery):
        """Генерация заголовка в зависимости от выбранного режима"""
        user_id = callback.from_user.id

        if 'session_repo' not in self.repositories:
            await callback.answer("❌ Репозитории не инициализированы")
            return

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session:
            await callback.answer("❌ Сессия не найдена")
            return

        # Определяем способ генерации
        generation_mode = session.generation_mode

        if generation_mode == 'advanced':
            # Продвинутая генерация
            await self._generate_title_advanced(callback, session)
        else:
            # Простая генерация
            await self._generate_title_simple(callback, session)

    # Добавьте новый метод для сбора данных:
    async def handle_collect_data(self, callback: CallbackQuery):
        """Сбор данных для продвинутой генерации"""
        user_id = callback.from_user.id

        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session or session.generation_mode != 'advanced':
            await callback.answer("❌ Некорректный режим генерации")
            return

        await callback.message.edit_text("🔍 <b>Собираю данные с MPStats...</b>")

        try:
            # Создаем тестовые данные
            test_file_path = await self._create_test_data({
                'category': session.category_id,
                'purpose': session.purpose,
                'additional_params': session.additional_params if session.additional_params else [],
                'user_id': user_id,
                'session_id': session.id
            })

            if test_file_path and os.path.exists(test_file_path):
                # Обновляем шаг сессии
                session.current_step = "data_scraped"
                session_repo.update(session.id, current_step="data_scraped")

                # Показываем кнопку для генерации
                builder = InlineKeyboardBuilder()
                builder.button(text="🤖 Сгенерировать заголовок", callback_data="generate_title")

                await callback.message.edit_text(
                    "✅ <b>Данные успешно собраны!</b>\n\n"
                    "Теперь можно сгенерировать заголовок:",
                    reply_markup=builder.as_markup()
                )
            else:
                await callback.message.edit_text("❌ Не удалось собрать данные")

        except Exception as e:
            self.logger.error(f"Ошибка сбора данных: {e}")
            await callback.message.edit_text("❌ Ошибка при сборе данных")

    async def _generate_title_simple(self, callback: CallbackQuery, session):
        """Простая генерация заголовка через OpenAI"""
        user_id = callback.from_user.id

        await callback.message.edit_text("🚀 <b>Генерирую заголовок (простой режим)...</b>")

        try:
            # Получаем данные категории
            category_repo = self.repositories['category_repo']
            category = category_repo.get_by_id(session.category_id)

            if not category:
                await callback.message.edit_text("❌ Категория не найдена")
                return

            # Используем OpenAI сервис напрямую
            if 'openai' not in self.services:
                await callback.message.edit_text("❌ Сервис OpenAI не инициализирован")
                return

            openai_service = self.services['openai']

            # Формируем промпт для генерации заголовка
            prompt = self._build_simple_title_prompt(session, category)

            # Генерируем заголовок
            generated_title = await openai_service.generate_title(
                category=category.name,
                purpose=session.purpose,
                keywords=[],  # Для простой генерации не используем ключевые слова
                additional_params=session.additional_params if session.additional_params else [],
                system_prompt=getattr(category, 'system_prompt_title', '')
            )

            if not generated_title:
                await callback.message.edit_text("❌ Не удалось сгенерировать заголовок")
                return

            # Генерируем ключевые слова на основе заголовка
            keywords_prompt = self._build_keywords_prompt(generated_title, category.name)

            # Для простой генерации используем заголовок для извлечения ключевых слов
            if hasattr(openai_service, 'generate_text'):
                keywords_text = await openai_service.generate_text(
                    prompt=keywords_prompt,
                    max_tokens=100
                )
                keywords = self._parse_keywords(keywords_text)
            else:
                # Альтернативный способ - использовать базовые ключевые слова
                keywords = [category.name, session.purpose]

            # Сохраняем результаты в сессии (используем репозиторий из self.repositories)
            session_repo = self.repositories['session_repo']
            session.generated_title = generated_title
            session.keywords = keywords
            session.current_step = "title_generated"

            # Используем метод update из BaseRepository через репозиторий сессий
            session_repo.update(
                session.id,
                generated_title=generated_title,
                keywords=keywords,
                current_step="title_generated"
            )

            # Показываем заголовок с кнопками
            builder = InlineKeyboardBuilder()
            builder.button(text="✅ Принять", callback_data=f"approve_title_{session.id}")
            builder.button(text="🔄 Перегенерировать", callback_data="regenerate_title")
            builder.button(text="📝 Изменить параметры", callback_data="change_params")
            builder.adjust(1)

            await callback.message.edit_text(
                f"📝 <b>Предлагаю заголовок (простая генерация):</b>\n\n"
                f"<code>{generated_title}</code>\n\n"
                f"🔑 <b>Ключевые слова:</b> {', '.join(keywords[:8]) if keywords else 'не сгенерированы'}",
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка простой генерации: {e}", exc_info=True)
            await callback.message.edit_text(
                f"❌ <b>Ошибка генерации:</b> {str(e)[:200]}\n\n"
                "Попробуйте изменить параметры или начать заново с /reset"
            )

        await callback.answer()


    def _build_simple_title_prompt(self, session, category) -> str:
        """Создать промпт для простой генерации заголовка"""
        return f"""
        Создай продающий заголовок для товара на маркетплейсе со следующими параметрами:

        Категория: {category.name}
        Назначение товара: {session.purpose}
        Дополнительные параметры: {', '.join(session.additional_params) if session.additional_params else 'нет'}

        Требования к заголовку:
        1. Максимально продающий и привлекательный
        2. Включает основные преимущества товара
        3. Соответствует категории "{category.name}"
        4. Оптимизирован для поиска на маркетплейсе
        5. Длина 5-7 слов
        6. Не используй HTML теги
        7. Пиши на русском языке
        8. Не используй специальные символы
        """

    def _build_keywords_prompt(self, title: str, category_name: str) -> str:
        """Создать промпт для генерации ключевых слов"""
        return f"""
        Извлеки 8-12 ключевых слов из этого заголовка для маркетплейса:

        Заголовок: {title}
        Категория: {category_name}

        Требования к ключевым словам:
        1. Релевантные товару
        2. Популярные для поиска на маркетплейсах
        3. Без стоп-слов
        4. В именительном падеже
        5. Разделяй запятыми

        Верни только список ключевых слов через запятую.
        """

    def _parse_keywords(self, text: str) -> list:
        """Парсить ключевые слова из текста"""
        if not text:
            return []

        # Удаляем лишние символы и разбиваем
        keywords = []
        for word in text.replace('\n', ',').split(','):
            word = word.strip().strip('.').strip()
            if word and len(word) > 1 and word.lower() not in ['и', 'в', 'на', 'для', 'с']:
                keywords.append(word)

        return keywords[:12]  # Ограничиваем количество

    async def _generate_title_advanced(self, callback: CallbackQuery, session):
        """Продвинутая генерация заголовка с MPStats"""
        user_id = callback.from_user.id

        await callback.message.edit_text("🤖 <b>Загружаю ключевые слова...</b>")

        try:
            # В продвинутой генерации мы создаем данные на лету
            scraper_params = {
                'category': session.category_id,
                'purpose': session.purpose,
                'additional_params': session.additional_params if session.additional_params else [],
                'user_id': user_id,
                'session_id': session.id
            }

            # Создаем тестовые данные
            test_file_path = await self._create_test_data(scraper_params)

            if not test_file_path or not os.path.exists(test_file_path):
                await callback.message.edit_text("❌ Не удалось загрузить ключевые слова")
                return

            keywords = await self._load_keywords_from_json(test_file_path)

            if not keywords:
                await callback.message.edit_text("❌ Не удалось загрузить ключевые слова")
                return

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

            # Используем загруженные ключевые слова
            result = await content_service.generate_content_workflow(
                category_name=category.name,
                purpose=session.purpose,
                additional_params=session.additional_params if session.additional_params else [],
                category_data=category_data,
                keywords=keywords
            )

            # Сохраняем результаты в сессии
            session.generated_title = result['title']
            session.keywords = result['keywords']
            session.current_step = "title_generated"
            session_repo = self.repositories['session_repo']
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
            builder.button(text="📝 Изменить параметры", callback_data="change_params")  # Новая кнопка
            builder.adjust(1)

            await callback.message.edit_text(
                f"📝 <b>Предлагаю заголовок (продвинутая генерация):</b>\n\n"
                f"<code>{result['title']}</code>\n\n"
                f"🔑 <b>Ключевые слова:</b> {', '.join(result['keywords'][:8])}...",
                reply_markup=builder.as_markup()
            )

        except Exception as e:
            self.logger.error(f"❌ Ошибка продвинутой генерации: {e}", exc_info=True)
            await callback.message.edit_text(
                f"❌ <b>Ошибка генерации:</b> {str(e)[:200]}\n\n"
                "Попробуйте изменить параметры или начать заново с /reset"
            )

        await callback.answer()


    # Остальные методы остаются без изменений...
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