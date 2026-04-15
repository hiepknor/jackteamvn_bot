from typing import Optional, List, Tuple, Dict, Any
from database.connection import db
from utils.logger import logger


class ProductRepository:
    """Repository for Jack Stock Bot product operations"""
    
    @staticmethod
    async def count() -> int:
        async with db.get_cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) AS total FROM products")
            row = await cursor.fetchone()
            return int(row["total"]) if row else 0
    
    @staticmethod
    async def create(raw_text: str, parsed_data: Dict[str, Any], user_id: int) -> Optional[int]:
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                INSERT INTO products 
                (raw_text, brand, model, dial_desc, condition, date_info, 
                 price_text, currency, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                raw_text,
                parsed_data.get("brand"),
                parsed_data.get("model"),
                parsed_data.get("dial_desc"),
                parsed_data.get("condition"),
                parsed_data.get("date_info"),
                parsed_data.get("price_text"),
                parsed_data.get("currency"),
                parsed_data.get("note"),
            ))
            product_id = cursor.lastrowid
            
            # Audit log
            await cursor.execute("""
                INSERT INTO audit_log (user_id, action, entity_type, entity_id, new_value)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, "CREATE", "product", product_id, raw_text))
            
            logger.info(f"Product created: ID={product_id}")
            return product_id
    
    @staticmethod
    async def get_by_id(product_id: int) -> Optional[Dict[str, Any]]:
        async with db.get_cursor() as cursor:
            await cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    async def get_all(limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        async with db.get_cursor() as cursor:
            sql = "SELECT * FROM products ORDER BY id DESC"
            params: Tuple = ()
            if limit:
                sql += " LIMIT ? OFFSET ?"
                params = (limit, offset)
            await cursor.execute(sql, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    async def search(query: str, limit: Optional[int] = 50) -> List[Dict[str, Any]]:
        search_term = f"%{query.strip()}%"
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                SELECT * FROM products
                WHERE raw_text LIKE ?
                   OR COALESCE(model, '') LIKE ?
                   OR COALESCE(dial_desc, '') LIKE ?
                   OR COALESCE(note, '') LIKE ?
                   OR COALESCE(brand, '') LIKE ?
                ORDER BY id DESC
                LIMIT ?
            """, (search_term, search_term, search_term, search_term, search_term, limit or 50))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    async def update(product_id: int, raw_text: str, parsed_data: Dict[str, Any], 
                     user_id: int, old_data: Dict[str, Any]) -> bool:
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                UPDATE products
                SET raw_text = ?, brand = ?, model = ?, dial_desc = ?, condition = ?,
                    date_info = ?, price_text = ?, currency = ?, note = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                raw_text,
                parsed_data.get("brand"),
                parsed_data.get("model"),
                parsed_data.get("dial_desc"),
                parsed_data.get("condition"),
                parsed_data.get("date_info"),
                parsed_data.get("price_text"),
                parsed_data.get("currency"),
                parsed_data.get("note"),
                product_id,
            ))
            updated = cursor.rowcount > 0
            
            if updated:
                await cursor.execute("""
                    INSERT INTO audit_log 
                    (user_id, action, entity_type, entity_id, old_value, new_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, "UPDATE", "product", product_id, 
                      str(old_data), str(parsed_data)))
                logger.info(f"Product updated: ID={product_id}")
            
            return updated
    
    @staticmethod
    async def delete(product_id: int, user_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        product = await ProductRepository.get_by_id(product_id)
        if not product:
            return False, None
        
        async with db.get_cursor() as cursor:
            await cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            deleted = cursor.rowcount > 0
            
            if deleted:
                await cursor.execute("""
                    INSERT INTO audit_log (user_id, action, entity_type, entity_id, old_value)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, "DELETE", "product", product_id, str(product)))
                logger.info(f"Product deleted: ID={product_id}")
            
            return deleted, product
    
    @staticmethod
    async def delete_batch(ids: List[int], user_id: int) -> Tuple[List[int], List[int]]:
        deleted_ids = []
        not_found_ids = []
        
        for product_id in ids:
            success, _ = await ProductRepository.delete(product_id, user_id)
            if success:
                deleted_ids.append(product_id)
            else:
                not_found_ids.append(product_id)
        
        return deleted_ids, not_found_ids
    
    @staticmethod
    async def get_stats() -> Dict[str, Any]:
        async with db.get_cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) AS total FROM products")
            total = (await cursor.fetchone())["total"]
            
            await cursor.execute("""
                SELECT brand, COUNT(*) AS count 
                FROM products 
                WHERE brand IS NOT NULL 
                GROUP BY brand 
                ORDER BY count DESC 
                LIMIT 10
            """)
            top_brands = await cursor.fetchall()
            
            return {
                "total_products": total,
                "top_brands": [dict(row) for row in top_brands]
            }
    
    @staticmethod
    async def get_audit_log(user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        async with db.get_cursor() as cursor:
            if user_id:
                await cursor.execute("""
                    SELECT * FROM audit_log 
                    WHERE user_id = ? 
                    ORDER BY id DESC 
                    LIMIT ?
                """, (user_id, limit))
            else:
                await cursor.execute("""
                    SELECT * FROM audit_log 
                    ORDER BY id DESC 
                    LIMIT ?
                """, (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


product_repo = ProductRepository()
