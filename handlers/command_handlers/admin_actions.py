from __future__ import annotations

from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

from database.models import backup_database
from database.repositories import product_repo
from handlers.filters import IsAdmin
from services.exporter import exporter
from services.normalizer import normalizer
from utils.logger import logger
from .shared import actor_tag, ensure_admin


def register(router: Router) -> None:
    @router.message(Command("export"), IsAdmin())
    async def cmd_export(message: Message):
        if not await ensure_admin(message):
            return

        total = await product_repo.count()
        if total == 0:
            await message.answer("📭 Hiện chưa có sản phẩm nào để xuất file.")
            return

        logger.info("Admin export started | %s | total=%s", actor_tag(message), total)
        wait_msg = await message.answer(f"⏳ Đang xuất {total} sản phẩm ra file...")

        try:
            txt_path = await exporter.export_to_txt()
            csv_path = await exporter.export_to_csv()

            await message.answer_document(FSInputFile(txt_path), caption=f"📄 File TXT ({total} sản phẩm)")
            await message.answer_document(FSInputFile(csv_path), caption=f"📊 File CSV ({total} sản phẩm)")
            logger.info(
                "Admin export success | %s | txt=%s | csv=%s",
                actor_tag(message),
                txt_path,
                csv_path,
            )
        except Exception as exc:
            logger.error("Admin export failed | %s | err=%s", actor_tag(message), exc, exc_info=exc)
            await message.answer(f"❌ Lỗi khi xuất file: {escape(str(exc))}")
        finally:
            try:
                await wait_msg.delete()
            except Exception:
                pass

    @router.message(Command("normalize"), IsAdmin())
    async def cmd_normalize(message: Message):
        if not await ensure_admin(message):
            return

        total = await product_repo.count()
        if total == 0:
            await message.answer("📭 Hiện chưa có sản phẩm nào để chuẩn hóa.")
            return

        logger.info("Admin normalize started | %s | total=%s", actor_tag(message), total)
        wait_msg = await message.answer(f"⏳ Đang chuẩn hóa {total} sản phẩm...")
        updated = 0
        skipped = 0
        failed = 0
        batch_size = 200
        offset = 0

        try:
            while True:
                rows = await product_repo.get_all(limit=batch_size, offset=offset)
                if not rows:
                    break

                for row in rows:
                    product_id = row["id"]
                    old_text = (row.get("normalized_text") or "").strip()
                    old_version = row.get("normalizer_version") or ""
                    new_text = normalizer.normalize(old_text)

                    if new_text == old_text and old_version == normalizer.VERSION:
                        skipped += 1
                        continue

                    success = await product_repo.update(
                        product_id,
                        new_text,
                        message.from_user.id,
                        row,
                        normalizer_version=normalizer.VERSION,
                    )
                    if success:
                        updated += 1
                    else:
                        failed += 1

                offset += batch_size

            logger.info(
                "Admin normalize completed | %s | updated=%s skipped=%s failed=%s",
                actor_tag(message),
                updated,
                skipped,
                failed,
            )
            await message.answer(
                "✅ <b>Chuẩn hóa hoàn tất</b>\n\n"
                f"🔁 Cập nhật: <b>{updated}</b>\n"
                f"⏭️ Bỏ qua: <b>{skipped}</b>\n"
                f"⚠️ Lỗi: <b>{failed}</b>\n"
                f"🧩 Phiên bản chuẩn hóa: <code>{normalizer.VERSION}</code>",
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.error("Normalize command failed: %s", exc, exc_info=exc)
            await message.answer(f"❌ Lỗi khi chuẩn hóa dữ liệu: {escape(str(exc))}", parse_mode="HTML")
        finally:
            try:
                await wait_msg.delete()
            except Exception:
                pass

    @router.message(Command("backup"), IsAdmin())
    async def cmd_backup(message: Message):
        if not await ensure_admin(message):
            return

        logger.info("Admin backup started | %s", actor_tag(message))
        wait_msg = await message.answer("⏳ Đang sao lưu database...")

        try:
            backup_path = await backup_database()
            if backup_path:
                logger.info("Admin backup success | %s | path=%s", actor_tag(message), backup_path)
                await message.answer(f"✅ Đã sao lưu: <code>{escape(backup_path)}</code>", parse_mode="HTML")
            else:
                await message.answer("⚠️ Sao lưu đang tắt trong cấu hình.")
        except Exception as exc:
            logger.error("Admin backup failed | %s | err=%s", actor_tag(message), exc, exc_info=exc)
            await message.answer(f"❌ Lỗi khi sao lưu: {escape(str(exc))}")
        finally:
            try:
                await wait_msg.delete()
            except Exception:
                pass
