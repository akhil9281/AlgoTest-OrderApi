"""
database client for API service to query orders and trades.
mainly for READ queries only
similar to a @Repository in Spring Boot.
"""

import asyncpg
import os
from typing import List, Optional, Dict, Any


class DatabaseClient:
    """
    database client for querying orders and trades.
    
    similar to Spring Data JPA repositories, but with raw SQL queries.
    """
    
    def __init__(self):
        """Initialize database client"""
        self.pool: Optional[asyncpg.Pool] = None
        # ideally in prod environment, we should be getting this via env variables and use a dedicated ORM like SQLAchemy
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/orderdb')
    
    async def connect(self):
        """Create connection pool to PostgreSQL"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=10
            )
            print(f"[DB_CLIENT] Connected to PostgresSQL database")
        except Exception as e:
            print(f"[DB_CLIENT] Error connecting to database: {e}")
            # allow API to start even if DB is unavailable, since WAL is still storing all the data
    
    async def disconnect(self):
        """closing the connection pool"""
        if self.pool:
            await self.pool.close()
            print("[DB_CLIENT] Disconnected from the database")
    
    async def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific order by ID.
        
        Args:
            order_id: Order ID
            
        Returns:
            Order data as dict, or None if not found
        """
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT 
                        id, side, order_price, order_quantity,
                        avg_traded_price, traded_quantity, status,
                        created_at, updated_at
                    FROM orders
                    WHERE id = $1
                """, order_id)
                
                if row:
                    return {
                        "order_id": row['id'],
                        "side": row['side'],
                        "price_paise": row['order_price'],
                        "original_qty": row['order_quantity'],
                        "avg_traded_price_paise": row['avg_traded_price'] or 0,
                        "traded_qty": row['traded_quantity'],
                        "status": row['status'],
                        "created_at": str(row['created_at']),
                        "updated_at": str(row['updated_at'])
                    }
                return None
        
        except Exception as e:
            print(f"[DB_CLIENT] Error fetching order: {e}")
            return None
    
    async def get_all_orders(self) -> List[Dict[str, Any]]:
        """
        Fetch all orders.
        
        Returns:
            List of order data dicts
        """
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        id, side, order_price, order_quantity,
                        avg_traded_price, traded_quantity, status,
                        created_at, updated_at
                    FROM orders
                    ORDER BY created_at DESC
                    LIMIT 100
                """)
                
                return [
                    {
                        "order_id": row['id'],
                        "side": row['side'],
                        "price_paise": row['order_price'],
                        "original_qty": row['order_quantity'],
                        "avg_traded_price_paise": row['avg_traded_price'] or 0,
                        "traded_qty": row['traded_quantity'],
                        "status": row['status'],
                        "created_at": str(row['created_at']),
                        "updated_at": str(row['updated_at'])
                    }
                    for row in rows
                ]
        
        except Exception as e:
            print(f"[DB_CLIENT] Error fetching orders: {e}")
            return []
    
    async def get_all_trades(self) -> List[Dict[str, Any]]:
        """
        Fetch all trades.
        
        Returns:
            List of trade data dicts
        """
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        id, bid_order_id, ask_order_id,
                        traded_price, traded_quantity, created_at
                    FROM trades
                    ORDER BY created_at DESC
                    LIMIT 100
                """)
                
                return [
                    {
                        "trade_id": row['id'],
                        "bid_order_id": row['bid_order_id'],
                        "ask_order_id": row['ask_order_id'],
                        "price_paise": row['traded_price'],
                        "qty": row['traded_quantity'],
                        "timestamp": str(row['created_at'])
                    }
                    for row in rows
                ]
        
        except Exception as e:
            print(f"[DB_CLIENT] Error fetching trades: {e}")
            return []
