from typing import List, Dict, Any, Optional
from html import escape


class MessageFormatter:
    """Message formatter for Jack Stock Bot"""

    @staticmethod
    def _safe(value: Any) -> str:
        return escape(str(value)) if value is not None else "-"
    
    @staticmethod
    def format_product_short(row: Dict[str, Any]) -> str:
        product_id = MessageFormatter._safe(row.get("id", "N/A"))
        raw_preview = MessageFormatter._safe((row.get("raw_text") or "")[:100])
        return f"🔹 <code>#{product_id}</code> | <code>{raw_preview}</code>"
    
    @staticmethod
    def format_product_detail(row: Dict[str, Any]) -> str:
        condition_emoji = {
            "new": "🆕",
            "used": "🔄",
            "mint": "✨",
            "excellent": "⭐",
        }.get((row.get("condition") or "").lower(), "❓")
        
        return (
            f"🆔 <b>ID:</b> <code>{MessageFormatter._safe(row.get('id', 'N/A'))}</code>\n"
            f"📋 <b>Raw:</b> <code>{MessageFormatter._safe(row.get('raw_text', ''))}</code>\n"
            f"🏷️ <b>Brand:</b> {MessageFormatter._safe(row.get('brand'))}\n"
            f"🔢 <b>Model:</b> {MessageFormatter._safe(row.get('model'))}\n"
            f"🎨 <b>Desc:</b> {MessageFormatter._safe(row.get('dial_desc'))}\n"
            f"{condition_emoji} <b>Condition:</b> {MessageFormatter._safe(row.get('condition'))}\n"
            f"📅 <b>Date:</b> {MessageFormatter._safe(row.get('date_info'))}\n"
            f"💰 <b>Price:</b> {MessageFormatter._safe(row.get('price_text'))}\n"
            f"💱 <b>Currency:</b> {MessageFormatter._safe(row.get('currency'))}\n"
            f"📝 <b>Note:</b> {MessageFormatter._safe(row.get('note'))}\n"
            f"🕐 <b>Created:</b> {MessageFormatter._safe(row.get('created_at', 'N/A'))}\n"
            f"🔄 <b>Updated:</b> {MessageFormatter._safe(row.get('updated_at', 'N/A'))}"
        )
    
    @staticmethod
    def format_product_list(rows: List[Dict[str, Any]], title: str, 
                           total: Optional[int] = None) -> str:
        if not rows:
            return "📭 Hiện chưa có sản phẩm nào."
        
        lines = [f"<b>{escape(title)}</b>", ""]
        for row in rows:
            product_id = MessageFormatter._safe(row.get("id", "N/A"))
            raw_preview = MessageFormatter._safe((row.get("raw_text") or "")[:120])
            lines.append(f"• <code>#{product_id}</code> | <code>{raw_preview}</code>")

        if total is not None:
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
        lines = [
            "📊 <b>Thống kê hệ thống</b>",
            "",
            f"📦 Tổng sản phẩm: <b>{stats['total_products']}</b>",
            "",
            "🏆 <b>Top thương hiệu:</b>"
        ]
        
        top_brands = stats.get("top_brands", [])[:5]
        if not top_brands:
            lines.append("  • Chưa có dữ liệu phân loại thương hiệu")
        else:
            for brand_info in top_brands:
                lines.append(f"  • {MessageFormatter._safe(brand_info['brand'])}: {brand_info['count']}")
        
        return "\n".join(lines)

formatter = MessageFormatter()
