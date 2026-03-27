# app/utils/log_codes.py (полная версия)
"""
Коды логирования для унификации сообщений

Формат: [КАТЕГОРИЯ][КОД] - Описание
Категории:
- SYS: Системные операции
- DB: База данных
- BOT: Telegram бот
- SCR: Скрапинг MPStats
- GPT: OpenAI операции
- USR: Действия пользователя
- DATA: Обработка данных
- FLT: Фильтрация
- ERR: Ошибки
"""


class LogCodes:
    """Коды логирования с уровнями важности"""

    # ========== СИСТЕМНЫЕ КОДЫ (SYS) ==========
    SYS_START = "[SYS001] Бот запущен"
    SYS_STOP = "[SYS002] Бот остановлен"
    SYS_INIT = "[SYS003] Инициализация модуля: {module}"
    SYS_SHUTDOWN = "[SYS004] Завершение работы"
    SYS_CONFIG = "[SYS005] Конфигурация загружена"

    # ========== БАЗА ДАННЫХ (DB) ==========
    DB_CONNECT = "[DB001] Установлено соединение с БД"
    DB_DISCONNECT = "[DB002] Соединение с БД закрыто"
    DB_TABLES_CREATED = "[DB003] Созданы таблицы в БД"
    DB_RECORD_CREATED = "[DB004] Создана запись {table}: {id}"
    DB_RECORD_UPDATED = "[DB005] Обновлена запись {table}: {id}"
    DB_RECORD_DELETED = "[DB006] Удалена запись {table}: {id}"
    DB_RECORD_FOUND = "[DB007] Найдена запись {table}: {id}"
    DB_RECORD_NOT_FOUND = "[DB008] Запись не найдена {table}: {id}"
    DB_SESSION_ACTIVE = "[DB009] Активная сессия: {id}"
    DB_SESSION_CREATED = "[DB010] Создана новая сессия: {id}"
    DB_MIGRATION = "[DB011] Выполнена миграция: {migration}"

    # ========== ПОЛЬЗОВАТЕЛЬСКИЕ ДЕЙСТВИЯ (USR) ==========
    USR_START = "[USR001] Пользователь {user_id} запустил бота"
    USR_SELECT_CATEGORY = "[USR002] Выбрана категория: {category}"
    USR_SELECT_PURPOSE = "[USR003] Выбрано назначение: {purpose}"
    USR_ADD_PARAMS = "[USR004] Добавлены параметры: {count}"
    USR_COMPLETE_SETUP = "[USR005] Завершена настройка товара"
    USR_REQUEST_GENERATION = "[USR006] Запрос генерации {type} для {marketplace}"
    USR_FILTER_KEYWORDS = "[USR007] Запрос ручной фильтрации ключевых слов"
    USR_VIEW_SESSIONS = "[USR008] Просмотр истории сессий"
    USR_VIEW_SNAPSHOTS = "[USR009] Просмотр снимков генераций"
    USR_RESET_SESSION = "[USR010] Сброс сессии"

    # ========== СКРАПИНГ MPSTATS (SCR) ==========
    SCR_START = "[SCR001] Запуск скрапинга MPStats"
    SCR_DRIVER_INIT = "[SCR002] Инициализация Chrome драйвера"
    SCR_LOGIN = "[SCR003] Выполнен вход в MPStats"
    SCR_LOGIN_SKIP = "[SCR004] Использован сохраненный профиль"
    SCR_FORM_FILL = "[SCR005] Заполнена форма запроса"
    SCR_WAIT = "[SCR006] Ожидание загрузки данных ({time}с)"
    SCR_DOWNLOAD_START = "[SCR007] Начало скачивания файла"
    SCR_DOWNLOAD_COMPLETE = "[SCR008] Файл скачан: {filename} ({size} байт)"
    SCR_CLEANUP = "[SCR009] Очистка временных файлов"
    SCR_SUCCESS = "[SCR010] Скрапинг завершен успешно"
    SCR_ERROR = "[SCR011] Ошибка скрапинга: {error}"
    SCR_DRIVER_CLOSE = "[SCR012] Chrome драйвер закрыт"

    # ========== GPT ОПЕРАЦИИ (GPT) ==========
    GPT_START = "[GPT001] Запрос к GPT: {type}"
    GPT_KEYWORD_FILTER = "[GPT002] Фильтрация ключевых слов ({count} → {filtered})"
    GPT_TITLE_GEN = "[GPT003] Генерация заголовка {marketplace}"
    GPT_DESC_GEN = "[GPT004] Генерация описания {marketplace}"
    GPT_SUCCESS = "[GPT005] GPT ответ получен за {time}с"
    GPT_ERROR = "[GPT006] Ошибка GPT: {error}"
    GPT_RETRY = "[GPT007] Повторная попытка {attempt}/{max}"

    # ========== ОБРАБОТКА ДАННЫХ (DATA) ==========
    DATA_EXCEL_LOAD = "[DATA001] Загрузка Excel: {filename}"
    DATA_EXCEL_SHEETS = "[DATA002] Найдено листов: {count}"
    DATA_KEYWORDS_EXTRACT = "[DATA003] Извлечено ключевых слов: {count}"
    DATA_KEYWORDS_FILTERED = "[DATA004] Отфильтровано ключевых слов: {count}"
    DATA_JSON_SAVE = "[DATA005] Сохранен JSON: {filename}"
    DATA_JSON_DELETE = "[DATA006] Удален JSON: {filename}"
    DATA_JSON_LOAD = "[DATA007] Загружен JSON: {filename}"

    # ========== ФИЛЬТРАЦИЯ (FLT) ==========
    FLT_START = "[FLT001] Начало ручной фильтрации"
    FLT_TOGGLE = "[FLT002] Изменен статус слова: {keyword}"
    FLT_ADD_KEYWORDS = "[FLT003] Добавлено ключевых слов: {count}"
    FLT_COMPLETE = "[FLT004] Фильтрация завершена: {total} → {filtered}"
    FLT_CANCEL = "[FLT005] Фильтрация отменена"

    # ========== ГЕНЕРАЦИЯ КОНТЕНТА (GEN) ==========
    GEN_MENU_SHOW = "[GEN001] Показано меню генерации"
    GEN_START = "[GEN002] Начало генерации {type} для {marketplace}"
    GEN_SUCCESS = "[GEN003] Генерация завершена: {length} символов"
    GEN_SAVE = "[GEN004] Результат сохранен в БД"
    GEN_SNAPSHOT = "[GEN005] Создан снимок: {id}"
    GEN_BACK_TO_DATA = "[GEN006] Возврат к данным сессии"

    # ========== ОШИБКИ (ERR) ==========
    ERR_SESSION_NOT_FOUND = "[ERR001] Сессия не найдена: {id}"
    ERR_CATEGORY_NOT_FOUND = "[ERR002] Категория не найдена: {id}"
    ERR_OPENAI = "[ERR003] Ошибка OpenAI API: {error}"
    ERR_MPSTATS = "[ERR004] Ошибка MPStats: {error}"
    ERR_DATABASE = "[ERR005] Ошибка БД: {error}"
    ERR_VALIDATION = "[ERR006] Ошибка валидации: {error}"
    ERR_ACCESS = "[ERR007] Отказано в доступе: {user_id}"
    ERR_HANDLER = "[ERR008] Ошибка обработчика: {handler} - {error}"
    ERR_PARSE = "[ERR009] Ошибка парсинга: {data}"