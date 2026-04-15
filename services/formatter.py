from typing import List, Dict, Any, Optional


class MessageFormatter:
    """Message formatter for Jack Stock Bot"""
    
    @staticmethod
    def format_product_short(row: Dict[str, Any]) -> str:
        return f"🔹 #{row['id']} | {row['brand'] or 'N/A'} {row['model'] or 'N/A'} | {row['raw_text'][:50]}..."
    
    @staticmethod
    def format_product_detail(row: Dict[str, Any]) -> str:
        condition_emoji = {
            "new": "🆕",
            "used": "🔄",
            "mint": "✨",
            "excellent": "⭐",
        }.get((row.get("condition") or "").lower(), "❓")
        
        return (
            f"🆔 <b>ID:</b> <code>{row['id']}</code>\n"
            f"📋 <b>Raw:</b> <code>{row['raw_text']}</code>\n"
            f"🏷️ <b>Brand:</b> {row.get('brand') or '-'}\n"
            f"🔢 <b>Model:</b> {row.get('model') or '-'}\n"
            f"🎨 <b>Desc:</b> {row.get('dial_desc') or '-'}\n"
            f"{condition_emoji} <b>Condition:</b> {row.get('condition') or '-'}\n"
            f"📅 <b>Date:</b> {row.get('date_info') or '-'}\n"
            f"💰 <b>Price:</b> {row.get('price_text') or '-'}\n"
            f"💱 <b>Currency:</b> {row.get('currency') or '-'}\n"
            f"📝 <b>Note:</b> {row.get('note') or '-'}\n"
            f"🕐 <b>Created:</b> {row.get('created_at', 'N/A')}\n"
            f"🔄 <b>Updated:</b> {row.get('updated_at', 'N/A')}"
        )
    
    @staticmethod
    def format_product_list(rows: List[Dict[str, Any]], title: str, 
                           total: Optional[int] = None) -> str:
        if not rows:
            return "📭 Hiện chưa có sản phẩm nào."
        
        lines = [f"<b>{title}</b>", ""]
        
        grouped: Dict[str, List] = {}
        for row in rows:
            brand = (row.get("brand") or "OTHER").upper()
            grouped.setdefault(brand, []).append(row)

        for brand in sorted(grouped.keys()):
            lines.append(f"🏷️ <b>{brand}</b>")
            for row in grouped[brand]:
                lines.append(
                    f"  • <code>#{row.get('id', 'N/A')}</code> | "
                    f"{row.get('model') or 'N/A'} | "
                    f"{(row.get('price_text') or '-')} {(row.get('currency') or '')}".rstrip()
                )
            lines.append("")

        if total is not None:
            lines.append(f"📦 Tổng trong hệ thống: <b>{total}</b>")
            lines.append(f"📄 Hiển thị: <b>{len(rows)}</b>")

        return "\n".join(lines)

    @staticmethod
    def format_search_results(query: str, rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return f"😕 Không tìm thấy sản phẩm nào với từ khóa: <b>{query}</b>"

        lines = [
            f"🔍 <b>Kết quả tìm kiếm:</b> <code>{query}</code>",
            f"📄 Tìm thấy: <b>{len(rows)}</b> sản phẩm",
            "",
        ]
        for row in rows:
            lines.append(MessageFormatter.format_product_short(row))

        return "\n".join(lines)

    @staticmethod
    def format_confirmation(action: str, details: str) -> str:
        return (
            f"⚠️ <b>Xác nhận {action}?</b>\n"
            f"{details}\n\n"
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
        
        for brand_info in stats.get("top_brands", [])[:5]:
            lines.append(f"  • {brand_info['brand']}: {brand_info['count']}")
        
        return "\n".join(lines)

formatter = MessageFormatter()
