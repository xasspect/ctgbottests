# app/bot/handlers/category_handler.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler


class CategoryHandler(BaseMessageHandler):
    """Обработчик выбора категории и назначения"""

    def __init__(self, services: dict, repositories: dict):
        super().__init__(services, repositories)
        self.router = Router()

        # Пример категорий и назначений
        self.categories = {
            "electronics": {
                "name": "📱 Электроника",
                "description": "Смартфоны, планшеты, гаджеты и аксессуары",
                "purposes": {
                    "gaming": "🎮 Для игр",
                    "everyday": "📅 Повседневная",
                    "business": "💼 Бизнес",
                    "creative": "🎨 Для творчества"
                }
            },
            "clothing": {
                "name": "👕 Одежда и обувь",
                "description": "Одежда, обувь и аксессуары",
                "purposes": {
                    "sport": "🏃‍♂️ Спортивная",
                    "casual": "👖 Повседневная",
                    "office": "👔 Офисная",
                    "evening": "🌙 Вечерняя"
                }
            },
            "home": {
                "name": "🏠 Дом и сад",
                "description": "Товары для дома, мебель, декор",
                "purposes": {
                    "kitchen": "🍳 Для кухни",
                    "bedroom": "🛏 Для спальни",
                    "garden": "🌳 Для сада",
                    "bathroom": "🛁 Для ванной"
                }
            },
            "beauty": {
                "name": "💄 Красота и здоровье",
                "description": "Косметика, уход, здоровый образ жизни",
                "purposes": {
                    "skincare": "🧴 Уход за кожей",
                    "makeup": "💋 Макияж",
                    "hair": "💇‍♀️ Для волос",
                    "wellness": "🌿 Для здоровья"
                }
            }
        }

    async def register(self, dp):
        dp.include_router(self.router)
        self.router.message.register(self.show_categories, Command(commands=["categories"]))
        self.router.message.register(self.reset_session, Command(commands=["reset"]))
        self.router.message.register(self.handle_additional_params, F.text & ~F.command)
        self.router.callback_query.register(self.handle_category_select, F.data.startswith("category_"))
        self.router.callback_query.register(self.handle_purpose_select, F.data.startswith("purpose_"))

    async def show_categories(self, message: Message):
        """Показать список категорий"""
        user_id = message.from_user.id

        # Сначала создаем/получаем пользователя
        user_repo = self.repositories['user_repo']
        user = user_repo.get_or_create(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )

        # Создаем клавиатуру с категориями
        builder = InlineKeyboardBuilder()
        for category_id, category_data in self.categories.items():
            builder.button(
                text=category_data["name"],
                callback_data=f"category_{category_id}"
            )
        builder.adjust(1)

        await message.answer(
            "📁 <b>Выберите категорию товара:</b>",
            reply_markup=builder.as_markup()
        )

    async def handle_category_select(self, callback: CallbackQuery):
        """Обработка выбора категории"""
        user_id = callback.from_user.id
        category_id = callback.data.replace("category_", "")

        category_data = self.categories.get(category_id)
        if not category_data:
            await callback.answer("❌ Категория не найдена")
            return

        # Сначала создаем/получаем пользователя
        user_repo = self.repositories['user_repo']
        user = user_repo.get_or_create(
            telegram_id=user_id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name
        )

        # Сохраняем в сессию
        session_repo = self.repositories['session_repo']
        try:
            session = session_repo.create_new_session(
                user_id=user_id,
                category_id=category_id,
                current_step="category_selected"
            )

            # Показываем выбор назначения
            builder = InlineKeyboardBuilder()
            for purpose_id, purpose_name in category_data["purposes"].items():
                builder.button(
                    text=purpose_name,
                    callback_data=f"purpose_{category_id}_{purpose_id}"
                )
            builder.adjust(1)

            await callback.message.edit_text(
                f"✅ <b>Выбрана категория:</b> {category_data['name']}\n\n"
                f"📝 {category_data['description']}\n\n"
                "🎯 <b>Теперь выберите назначение товара:</b>",
                reply_markup=builder.as_markup()
            )
            await callback.answer()

        except Exception as e:
            self.logger.error(f"❌ Error creating session: {e}")
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

        await callback.message.edit_text(
            f"✅ <b>Категория:</b> {category_data['name']}\n"
            f"✅ <b>Назначение:</b> {purpose_name}\n\n"
            "📋 <b>Хотите добавить дополнительные параметры?</b>\n"
            "<i>Напишите через запятую, например: 'высокая производительность, AMOLED дисплей, долгая батарея'</i>\n\n"
            "🔸 Или отправьте <code>нет</code> чтобы продолжить без доп. параметров"
        )
        await callback.answer()

    async def handle_additional_params(self, message: Message):
        """Обработка ввода дополнительных параметров"""
        user_id = message.from_user.id
        params_text = message.text.strip().lower()

        # Проверяем активную сессию
        session_repo = self.repositories['session_repo']
        session = session_repo.get_active_session(user_id)

        if not session or session.current_step != "purpose_selected":
            await message.answer(
                "⚠️ Сначала выберите категорию и назначение с помощью <code>/categories</code>"
            )
            return

        additional_params = []

        if params_text != "нет":
            # Разбиваем параметры по запятой
            additional_params = [param.strip() for param in params_text.split(',') if param.strip()]

            await message.answer(
                f"✅ <b>Дополнительные параметры сохранены:</b>\n"
                f"{', '.join(additional_params)}\n\n"
                "🔄 <b>Готов к генерации контента!</b>\n\n"
                "Используйте <code>/generate</code> чтобы начать генерацию"
            )
        else:
            await message.answer(
                "🔄 <b>Готов к генерации контента без дополнительных параметров!</b>\n\n"
                "Используйте <code>/generate</code> чтобы начать генерацию"
            )

        # Сохраняем параметры
        session.additional_params = additional_params
        session.current_step = "params_added"
        session_repo.update(
            session.id,
            additional_params=additional_params,
            current_step="params_added"
        )

    async def reset_session(self, message: Message):
        """Сброс сессии"""
        user_id = message.from_user.id

        session_repo = self.repositories['session_repo']
        session_repo.deactivate_all_sessions(user_id)

        await message.answer(
            "🔄 <b>Сессия сброшена</b>\n"
            "Начните заново с <code>/categories</code>"
        )