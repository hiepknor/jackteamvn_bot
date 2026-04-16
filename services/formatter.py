from typing import List, Dict, Any, Optional
from html import escape


class MessageFormatter:
    """Message formatter for Jack Stock Bot"""

    @staticmethod
    def _safe(value: Any) -> str:
        return escape(str(value)) if value is not None else "-"

    @staticmethod
    def _display_text(row: Dict[str, Any]) -> str:
        return row.get("normalized_text") or row.get("raw_text") or ""
    
    @staticmethod
    def format_product_short(row: Dict[str, Any]) -> str:
        product_id = MessageFormatter._safe(row.get("id", "N/A"))
        text_preview = MessageFormatter._safe(MessageFormatter._display_text(row)[:90])
        suffix = "..." if len(MessageFormatter._display_text(row)) > 90 else ""
        return f"🔹 <code>#{product_id}</code> | <code>{text_preview}</code>{suffix}"
    
    @staticmethod
    def format_product_detail(row: Dict[str, Any]) -> str:
        return (
            f"🆔 <b>ID:</b> <code>{MessageFormatter._safe(row.get('id', 'N/A'))}</code>\n"
            f"📋 <b>Text:</b> <code>{MessageFormatter._safe(MessageFormatter._display_text(row))}</code>\n"
            f"🧩 <b>Normalizer:</b> <code>{MessageFormatter._safe(row.get('normalizer_version', 'N/A'))}</code>\n"
            f"🕐 <b>Created:</b> {MessageFormatter._safe(row.get('created_at', 'N/A'))}\n"
            f"🔄 <b>Updated:</b> {MessageFormatter._safe(row.get('updated_at', 'N/A'))}"
        )
    
    @staticmethod
    def format_product_list(
        rows: List[Dict[str, Any]],
        title: str,
        total: Optional[int] = None,
        page: Optional[int] = None,
        total_pages: Optional[int] = None,
    ) -> str:
        if not rows:
            return "📭 Hiện chưa có sản phẩm nào."
        
        lines = [f"<b>{escape(title)}</b>", ""]
        for row in rows:
            product_id = MessageFormatter._safe(row.get("id", "N/A"))
            display_text = MessageFormatter._display_text(row)
            text_preview = MessageFormatter._safe(display_text[:80])
            suffix = "..." if len(display_text) > 80 else ""
            lines.append(f"• <code>#{product_id}</code> | <code>{text_preview}</code>{suffix}")

        if total is not None:
            if page is not None and total_pages is not None:
                lines.append(f"🧭 Trang: <b>{page}/{total_pages}</b>")
            lines.append(f"📦 Tổng trong hệ thống: <b>{total}</b>")
            lines.append(f"📄 Hiển thị: <b>{len(rows)}</b>")

        return "\n".join(lines)

    @staticmethod
    def format_search_results(query: str, rows: List[Dict[str, Any]]) -> str:
        query_safe = MessageFormatter._safe(query)
        if not rows:
            return f"😕 Không tìm thấy sản phẩm nào với từ khóa: <b>{query_safe}</b>"

        lines = [
            f"🔍 <b>Kết quả tìm kiếm:</b> <code>{query_safe}</code>",
            f"📄 Tìm thấy: <b>{len(rows)}</b> sản phẩm",
            "",
        ]
        for row in rows:
            lines.append(MessageFormatter.format_product_short(row))

        return "\n".join(lines)

    @staticmethod
    def format_confirmation(action: str, details: str) -> str:
        return (
            f"⚠️ <b>Xác nhận {escape(action)}?</b>\n"
            f"{escape(details)}\n\n"
            f"Gõ <code>yes</code> để xác nhận hoặc nhập nội dung khác để hủy."
        )

    @staticmethod
    def format_stats(stats: Dict[str, Any]) -> str:
        """Format statistics message"""
        return (
            "📊 <b>Thống kê hệ thống</b>\n\n"
            f"📦 Tổng sản phẩm: <b>{stats['total_products']}</b>"
        )

formatter = MessageFormatter()
