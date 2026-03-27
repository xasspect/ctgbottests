# app/bot/handlers/snapshot_handler.py
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.bot.handlers.base_handler import BaseMessageHandler
import json
from datetime import datetime
import os
import pandas as pd
import tempfile
from app.utils.logger import log
from app.utils.log_codes import LogCodes


class SnapshotHandler(BaseMessageHandler):
    def __init__(self, config, services, repositories):
        super().__init__(config, services, repositories)
        self.router = Router()

    async def register(self, dp):
        """Регистрация обработчиков"""
        dp.include_router(self.router)

        self.router.callback_query.register(
            self.handle_show_snapshots,
            F.data == "show_snapshots"
        )
        self.router.callback_query.register(
            self.handle_view_snapshot,
            F.data.startswith("snapshot_view_")
        )
        self.router.callback_query.register(
            self.handle_export_snapshots,
            F.data == "export_snapshots"
        )
        self.router.callback_query.register(
            self.handle_back_to_snapshots,
            F.data == "back_to_snapshots"
        )
        self.router.callback_query.register(
            self.handle_refresh_snapshots,
            F.data == "refresh_snapshots"
        )

        log.info(LogCodes.SYS_INIT, module="SnapshotHandler")

    async def handle_show_snapshots(self, callback: CallbackQuery):
        """Показать список последних снимков"""
        await self.show_snapshots(callback.message)
        await callback.answer()

    async def show_snapshots(self, message: Message):
        """Показать последние 10 снимков из БД"""
        snapshot_repo = self.repositories.get('snapshot_repo')

        if not snapshot_repo:
            await message.answer("❌ Репозиторий снимков не найден")
            return

        snapshots = snapshot_repo.get_recent_snapshots(limit=10)

        if not snapshots:
            builder = InlineKeyboardBuilder()
            builder.button(text="🔄 Обновить", callback_data="refresh_snapshots")
            builder.button(text="🏠 Главное меню", callback_data="back_to_main_menu")
            builder.adjust(1)

            await message.edit_text(
                "📸 <b>В БД пока нет снимков генераций.</b>\n\n"
                "Сгенерируйте контент в меню генерации, и здесь появятся снимки.",
                reply_markup=builder.as_markup()
            )
            return

        text = "📸 <b>Последние снимки генераций</b>\n\n"
        text += f"Всего в БД: {snapshot_repo.get_total_count()}\n"
        text += "Показаны последние 10 снимков:\n\n"

        builder = InlineKeyboardBuilder()

        for snap in snapshots:
            content_type = f"{snap.marketplace.upper()} {snap.generation_type}"
            date_str = snap.created_at.strftime('%d.%m.%Y %H:%M')

            preview = ""
            if snap.wb_title:
                preview = snap.wb_title[:30] + "..."
            elif snap.ozon_title:
                preview = snap.ozon_title[:30] + "..."
            else:
                preview = f"{snap.generation_type} снимок"

            button_text = f"{date_str} - {content_type} (user: {snap.user_id}): {preview}"
            builder.button(
                text=button_text,
                callback_data=f"snapshot_view_{snap.id}"
            )

        builder.button(text="🔄 Обновить", callback_data="refresh_snapshots")
        builder.button(text="📊 Экспорт всех в Excel", callback_data="export_snapshots")
        builder.button(text="🏠 Главное меню", callback_data="back_to_main_menu")
        builder.adjust(1)

        await message.edit_text(text, reply_markup=builder.as_markup())

    async def handle_view_snapshot(self, callback: CallbackQuery):
        """Просмотр конкретного снимка"""
        snapshot_id = callback.data.replace("snapshot_view_", "")
        snapshot_repo = self.repositories.get('snapshot_repo')

        snapshot = snapshot_repo.get_by_id(snapshot_id)
        if not snapshot:
            await callback.answer("❌ Снимок не найден", show_alert=True)
            return

        text = (
            f"📸 <b>Снимок генерации</b>\n"
            f"🕐 {snapshot.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
            f"👤 Пользователь: {snapshot.user_id}\n\n"
            f"📁 <b>Контекст:</b>\n"
            f"• Категория: {snapshot.category_name} ({snapshot.category_id})\n"
            f"• Назначения: {', '.join(snapshot.purposes) if snapshot.purposes else 'нет'}\n"
            f"• Доп. параметры: {', '.join(snapshot.additional_params) if snapshot.additional_params else 'нет'}\n"
            f"• Ключевых слов: {len(snapshot.keywords) if snapshot.keywords else 0}\n\n"
            f"🎯 <b>Генерация:</b>\n"
            f"• Маркетплейс: {snapshot.marketplace}\n"
            f"• Тип: {snapshot.generation_type}\n\n"
        )

        if snapshot.wb_title:
            text += f"📝 <b>WB Title:</b>\n<code>{snapshot.wb_title}</code>\n\n"
        if snapshot.wb_short_desc:
            short_desc = snapshot.wb_short_desc[:200] + "..." if len(
                snapshot.wb_short_desc) > 200 else snapshot.wb_short_desc
            text += f"📋 <b>WB Short Desc:</b>\n{short_desc}\n\n"
        if snapshot.wb_long_desc:
            text += f"📖 <b>WB Long Desc:</b> {len(snapshot.wb_long_desc)} символов\n"
            text += f"<code>{snapshot.wb_long_desc[:200]}...</code>\n\n"
        if snapshot.ozon_title:
            text += f"🛍️ <b>Ozon Title:</b>\n<code>{snapshot.ozon_title}</code>\n\n"
        if snapshot.ozon_desc:
            text += f"📄 <b>Ozon Desc:</b> {len(snapshot.ozon_desc)} символов\n"
            text += f"<code>{snapshot.ozon_desc[:200]}...</code>\n\n"

        if snapshot.keywords:
            keywords_preview = "\n".join([f"• {kw}" for kw in snapshot.keywords[:10]])
            if len(snapshot.keywords) > 10:
                keywords_preview += f"\n• ... и ещё {len(snapshot.keywords) - 10}"
            text += f"🔑 <b>Ключевые слова (первые 10):</b>\n{keywords_preview}\n"

        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад к списку", callback_data="back_to_snapshots")
        builder.button(text="🏠 Главное меню", callback_data="back_to_main_menu")
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()

    async def handle_refresh_snapshots(self, callback: CallbackQuery):
        """Обновить список снимков"""
        await self.show_snapshots(callback.message)
        await callback.answer()

    async def handle_back_to_snapshots(self, callback: CallbackQuery):
        """Вернуться к списку снимков"""
        await self.show_snapshots(callback.message)
        await callback.answer()

    async def handle_export_snapshots(self, callback: CallbackQuery):
        """Экспорт всех снимков в Excel"""
        await callback.answer("🔄 Генерирую Excel файл...")

        try:
            snapshot_repo = self.repositories.get('snapshot_repo')
            snapshots = snapshot_repo.get_all_snapshots(limit=1000)

            if not snapshots:
                await callback.message.answer("❌ Нет снимков для экспорта")
                return

            data = []
            for s in snapshots:
                data.append({
                    'ID': s.id,
                    'Дата': s.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'Пользователь': s.user_id,
                    'Сессия': s.session_id,
                    'Маркетплейс': s.marketplace,
                    'Тип': s.generation_type,
                    'Категория': s.category_name,
                    'Назначения': ', '.join(s.purposes) if s.purposes else '',
                    'Доп. параметры': ', '.join(s.additional_params) if s.additional_params else '',
                    'Ключевых слов': len(s.keywords) if s.keywords else 0,
                    'WB Title': s.wb_title or '',
                    'WB Short Desc': (s.wb_short_desc[:100] + '...') if s.wb_short_desc and len(
                        s.wb_short_desc) > 100 else s.wb_short_desc or '',
                    'WB Long Desc длина': len(s.wb_long_desc) if s.wb_long_desc else 0,
                    'Ozon Title': s.ozon_title or '',
                    'Ozon Desc длина': len(s.ozon_desc) if s.ozon_desc else 0,
                })

            df = pd.DataFrame(data)

            filename = f"snapshots_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = os.path.join(tempfile.gettempdir(), filename)

            df.to_excel(filepath, index=False)
            log.info(LogCodes.DATA_EXCEL_LOAD, filename=filename)

            document = FSInputFile(filepath)
            await callback.message.answer_document(
                document=document,
                caption=f"📊 Экспорт всех снимков ({len(snapshots)} записей)"
            )

            try:
                os.remove(filepath)
            except Exception:
                pass

        except Exception as e:
            log.error(LogCodes.ERR_DATABASE, error=f"Export: {e}")
            await callback.message.answer(f"❌ Ошибка экспорта: {str(e)[:200]}")

        await callback.answer()