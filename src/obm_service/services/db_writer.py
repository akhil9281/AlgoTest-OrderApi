"""
async database writer for PostgreSQL.
persists data in PostgreSQL asynchronously to avoid blocking the matching engine.

ideally in a production env
"""

import os
from typing import Optional

import asyncpg

from shared.models import OrderRecord, TradeRecord


class DatabaseWriter:
    """
    Handles async database operations for order and trade persistence.
    """
    
    def __init__(self):
        """Initialize database writer"""
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/orderdb')
    
    async def connect(self):
        """Create connection pool to PostgreSQL"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=10
            )
            print(f"[DB_WRITER] Connected to database: {self.database_url}")
        except Exception as e:
            print(f"[DB_WRITER] Error connecting to database: {e}")
            raise
    
    async def disconnect(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            print("[DB_WRITER] Disconnected from database")
    
    async def insert_order(self, order: OrderRecord):
        """
        Insert a new order into the database.
        
        Args:
            order: OrderRecord to insert
        """
        if not self.pool:
            print("[DB_WRITER] Database pool not initialized")
            return
        
        try:
            # Parse timestamps if they are strings
            from datetime import datetime
            created_at = order.created_timestamp
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    pass # Let asyncpg handle it or fail
            
            updated_at = order.updated_timestamp
            if isinstance(updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at)
                except ValueError:
                    pass

            print(f"[DB_WRITER] Attempting to insert order {order.order_id}")
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO orders (
                        id, side, order_price, order_quantity,
                        avg_traded_price, traded_quantity, status,
                        created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                    order.order_id,
                    order.side,
                    order.price_paise,
                    order.original_qty,
                    order.avg_traded_price_paise,
                    order.traded_qty,
                    order.status,
                    created_at,
                    updated_at
                )
                print(f"[DB_WRITER] Successfully inserted order {order.order_id}")
        except Exception as e:
            print(f"[DB_WRITER] Error inserting order {order.order_id}: {e}")
            import traceback
            traceback.print_exc()
    
    async def update_order(self, order: OrderRecord):
        """
        Update an existing order in the database.
        
        Args:
            order: OrderRecord to update
        """
        if not self.pool:
            print("[DB_WRITER] Database pool not initialized")
            return
        
        try:
            # Parse timestamps if they are strings
            from datetime import datetime
            updated_at = order.updated_timestamp
            if isinstance(updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at)
                except ValueError:
                    pass

            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE orders
                    SET order_price = $2,
                        order_quantity = $3,
                        avg_traded_price = $4,
                        traded_quantity = $5,
                        status = $6,
                        updated_at = $7
                    WHERE id = $1
                """,
                    order.order_id,
                    order.price_paise,
                    order.original_qty,
                    order.avg_traded_price_paise,
                    order.traded_qty,
                    order.status,
                    updated_at
                )
                print(f"[DB_WRITER] Updated order {order.order_id}")
        except Exception as e:
            print(f"[DB_WRITER] Error updating order {order.order_id}: {e}")
    
    async def insert_trade(self, trade: TradeRecord):
        """
        Insert a new trade into the database.
        
        Args:
            trade: TradeRecord to insert
        """
        if not self.pool:
            print("[DB_WRITER] Database pool not initialized")
            return
        
        try:
            # Parse timestamps if they are strings
            from datetime import datetime
            created_at = trade.timestamp
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except ValueError:
                    pass

            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO trades (
                        id, bid_order_id, ask_order_id,
                        traded_price, traded_quantity, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    trade.trade_id,
                    trade.bid_order_id,
                    trade.ask_order_id,
                    trade.price_paise,
                    trade.qty,
                    created_at
                )
                print(f"[DB_WRITER] Inserted trade {trade.trade_id}")
        except Exception as e:
            print(f"[DB_WRITER] Error inserting trade {trade.trade_id}: {e}")
    
    async def get_all_orders(self):
        """
        Fetch all orders from database.
        
        Returns:
            List of order records as dicts
        """
        if not self.pool:
            print("[DB_WRITER] Database pool not initialized")
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
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DB_WRITER] Error fetching orders: {e}")
            return []
    
    async def get_all_trades(self):
        """
        Fetch all trades from database.
        
        Returns:
            List of trade records as dicts
        """
        if not self.pool:
            print("[DB_WRITER] Database pool not initialized")
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        id, bid_order_id, ask_order_id,
                        traded_price, traded_quantity, created_at
                    FROM trades
                    ORDER BY created_at DESC
                """)
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DB_WRITER] Error fetching trades: {e}")
            return []
