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
    async def create(normalized_text: str, user_id: int, normalizer_version: str = "v1") -> Optional[int]:
        async with db.get_cursor() as cursor:
            await cursor.execute(
                "INSERT INTO products (normalized_text, normalizer_version) VALUES (?, ?)",
                (normalized_text, normalizer_version),
            )
            product_id = cursor.lastrowid
            
            # Audit log
            await cursor.execute("""
                INSERT INTO audit_log (user_id, action, entity_type, entity_id, new_value)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, "CREATE", "product", product_id, normalized_text))
            
            logger.info(f"Product created: ID={product_id}")
            return product_id
    
    @staticmethod
    async def get_by_id(product_id: int) -> Optional[Dict[str, Any]]:
        async with db.get_cursor() as cursor:
            await cursor.execute(
                """
                SELECT id, normalized_text, normalizer_version, created_at, updated_at
                FROM products
                WHERE id = ?
                """,
                (product_id,),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    async def get_all(limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        async with db.get_cursor() as cursor:
            sql = """
                SELECT id, normalized_text, normalizer_version, created_at, updated_at
                FROM products
                ORDER BY id DESC
            """
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
                SELECT id, normalized_text, normalizer_version, created_at, updated_at
                FROM products
                WHERE normalized_text LIKE ?
                ORDER BY id DESC
                LIMIT ?
            """, (search_term, limit or 50))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    async def update(
        product_id: int,
        normalized_text: str,
        user_id: int,
        old_data: Dict[str, Any],
        normalizer_version: str = "v1",
    ) -> bool:
        async with db.get_cursor() as cursor:
            await cursor.execute("""
                UPDATE products
                SET normalized_text = ?, normalizer_version = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                normalized_text,
                normalizer_version,
                product_id,
            ))
            updated = cursor.rowcount > 0
            
            if updated:
                await cursor.execute("""
                    INSERT INTO audit_log 
                    (user_id, action, entity_type, entity_id, old_value, new_value)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, "UPDATE", "product", product_id, 
                      str(old_data), normalized_text))
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
            return {"total_products": total}
    
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
