# app/utils/button_utils.py
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_title_buttons(session_id: str, include_back: bool = True):
    """Создать кнопки для заголовка"""
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Принять", callback_data=f"approve_title_{session_id}")
    builder.button(text="🔄 Перегенерировать", callback_data="regenerate_title")
    builder.button(text="📝 Изменить параметры", callback_data="change_params")

    if include_back:
        builder.button(text="↩️ Назад", callback_data="back_to_title")

    builder.adjust(1)
    return builder


def create_description_buttons(session_id: str, desc_type: str):
    """Создать кнопки для описания"""
    builder = InlineKeyboardBuilder()

    if desc_type == "both":
        builder.button(text="✅ Принять описания", callback_data=f"approve_desc_both_{session_id}")
        builder.button(text="🔄 Перегенерировать", callback_data=f"regenerate_desc_both_{session_id}")
    else:
        builder.button(text="✅ Принять", callback_data=f"approve_desc_{desc_type}_{session_id}")
        builder.button(text="🔄 Перегенерировать", callback_data=f"regenerate_desc_{desc_type}_{session_id}")

    # Дополнительные кнопки в зависимости от типа
    if desc_type == "short":
        builder.button(text="📖 Сгенерировать подробное", callback_data=f"generate_long_{session_id}")
        builder.button(text="⚡ Оба описания", callback_data=f"generate_both_{session_id}")
    elif desc_type == "long":
        builder.button(text="📋 Сгенерировать краткое", callback_data=f"generate_short_{session_id}")
        builder.button(text="⚡ Оба описания", callback_data=f"generate_both_{session_id}")
    elif desc_type == "both":
        builder.button(text="📋 Только краткое", callback_data=f"generate_short_{session_id}")
        builder.button(text="📖 Только подробное", callback_data=f"generate_long_{session_id}")

    builder.button(text="🏠 Меню", callback_data="back_to_menu_from_generation")
    builder.adjust(1)
    return builder