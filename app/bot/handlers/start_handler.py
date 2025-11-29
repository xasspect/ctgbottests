from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from app.bot.handlers.base_handler import BaseMessageHandler


class StartHandler(BaseMessageHandler):
    """Обработчик команды /start и /help"""

    def __init__(self, services: dict, repositories: dict):
        super().__init__(services, repositories)
        self.router = Router()

    async def register(self, dp):
        dp.include_router(self.router)
        self.router.message.register(self.start_command, Command(commands=["start"]))
        self.router.message.register(self.help_command, Command(commands=["help"]))

    async def start_command(self, message: Message):
        """Обработчик /start"""
        user = message.from_user
        user_id = user.id

        # Сохраняем/получаем пользователя в БД
        user_repo = self.repositories['user_repo']
        db_user = user_repo.get_or_create(
            telegram_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )

        welcome_text = (
            "🤖 <b>Добро пожаловать в MPStats Content Generator!</b>\n\n"
            "Я помогу вам создать <b>продающие заголовки и описания</b> "
            "для товаров на маркетплейсах.\n\n"
            "📝 <b>Для начала работы:</b>\n"
            "1. Используйте <code>/categories</code> - выбрать категорию товара\n"
            "2. Укажите назначение товара\n"
            "3. Добавьте параметры (опционально)\n"
            "4. Получите готовый контент!\n\n"
            "⚡ <b>Основные команды:</b>\n"
            "/categories - выбрать категорию\n"
            "/reset - начать заново\n"
            "/help - помощь"
        )

        await message.answer(welcome_text)

    async def help_command(self, message: Message):
        """Обработчик /help"""
        help_text = (
            "📖 <b>Помощь по боту</b>\n\n"
            "🎯 <b>Как работает бот:</b>\n"
            "1. Выбираете категорию товара\n"
            "2. Указываете назначение (например: 'для игр', 'повседневная')\n"
            "3. Добавляете параметры через запятую (опционально)\n"
            "4. Получаете ключевые слова из MPStats\n"
            "5. Генерируете заголовок и описания\n\n"
            "🔄 <b>Процесс генерации:</b>\n"
            "• AI анализирует ключевые слова\n"
            "• Фильтрует нерелевантные слова\n"
            "• Создает продающий заголовок\n"
            "• Генерирует описания разного формата\n\n"
            "⚡ <b>Команды:</b>\n"
            "/start - начать работу\n"
            "/categories - выбрать категорию\n"
            "/reset - сбросить сессию\n"
            "/help - эта справка"
        )

        await message.answer(help_text)