"""
Redis Streams consumer for order queue.

Consumes order requests from the order_queue and processes them through the matching engine.
"""

import json
import asyncio
from typing import Optional, Dict, Any
from shared.models import OrderRecord, OrderStatus
from shared.constants import (
    REDIS_ORDER_QUEUE,
    REDIS_OBM_CONSUMER_GROUP,
    REDIS_OBM_CONSUMER_NAME,
    OperationType
)
from ..order_book import OrderBook
from ..matching_engine import MatchingEngine
from ..wal import WAL


class OrderConsumer:
    """
    Consumes orders from Redis Streams and processes them.
    """
    
    def __init__(
        self,
        redis_client,
        order_book: OrderBook,
        matching_engine: MatchingEngine,
        wal: WAL,
        event_publisher,
        db_writer=None  # Optional database writer
    ):
        """
        Initialize order consumer.
        
        Args:
            redis_client: Redis client instance
            order_book: OrderBook instance
            matching_engine: MatchingEngine instance
            wal: WAL instance
            event_publisher: EventPublisher instance to publish trades
            db_writer: Optional DatabaseWriter instance for persistence
        """
        self.redis_client = redis_client
        self.order_book = order_book
        self.matching_engine = matching_engine
        self.wal = wal
        self.event_publisher = event_publisher
        self.db_writer = db_writer
        self.running = False
    
    async def start(self):
        """Start consuming from order queue"""
        self.running = True
        
        # Create consumer group if it doesn't exist
        try:
            await self.redis_client.xgroup_create(
                name=REDIS_ORDER_QUEUE,
                groupname=REDIS_OBM_CONSUMER_GROUP,
                id='0',
                mkstream=True
            )
            print(f"[CONSUMER] Created consumer group '{REDIS_OBM_CONSUMER_GROUP}'")
        except Exception as e:
            # Group already exists
            print(f"[CONSUMER] Consumer group already exists: {e}")
        
        print(f"[CONSUMER] Starting to consume from '{REDIS_ORDER_QUEUE}'...")
        
        # Consume loop
        while self.running:
            try:
                # Read from stream with blocking
                messages = await self.redis_client.xreadgroup(
                    groupname=REDIS_OBM_CONSUMER_GROUP,
                    consumername=REDIS_OBM_CONSUMER_NAME,
                    streams={REDIS_ORDER_QUEUE: '>'},
                    count=1,
                    block=1000  # Block for 1 second
                )
                
                if messages:
                    for stream_name, stream_messages in messages:
                        for message_id, message_data in stream_messages:
                            await self._process_message(message_id, message_data)
                
                # Small sleep to avoid tight loop
                await asyncio.sleep(0.01)
                
            except Exception as e:
                print(f"[CONSUMER] Error consuming from stream: {e}")
                await asyncio.sleep(1)
    
    async def stop(self):
        """Stop consuming"""
        self.running = False
        print("[CONSUMER] Stopped")
    
    async def _process_message(self, message_id: str, message_data: Dict[str, Any]):
        """
        Process a single message from the queue.
        
        Args:
            message_id: Redis stream message ID
            message_data: Message payload
        """
        try:
            # Parse message
            operation = message_data.get('operation')
            data_json = message_data.get('data', '{}')
            data = json.loads(data_json)
            
            print(f"[CONSUMER] Processing {operation} operation: {data}")
            
            # Handle different operations
            if operation == OperationType.CREATE:
                await self._handle_create_order(data)
            
            elif operation == OperationType.MODIFY:
                await self._handle_modify_order(data)
            
            elif operation == OperationType.CANCEL:
                await self._handle_cancel_order(data)
            
            elif operation == OperationType.FETCH:
                # FETCH is read-only, no processing needed here
                # The API service will query the state directly
                pass
            
            # Acknowledge message
            await self.redis_client.xack(
                REDIS_ORDER_QUEUE,
                REDIS_OBM_CONSUMER_GROUP,
                message_id
            )
            
        except Exception as e:
            print(f"[CONSUMER] Error processing message {message_id}: {e}")
            import traceback
            traceback.print_exc()
    
    async def _handle_create_order(self, data: Dict[str, Any]):
        """
        Handle CREATE order operation.
        
        Args:
            data: Order data
        """
        # Create OrderRecord
        order = OrderRecord.from_dict(data)
        
        # Log to WAL before processing
        self.wal.append('INSERT', 'ORDER', order.to_dict())
        
        # Persist to database (async, non-blocking)
        if self.db_writer:
            await self.db_writer.insert_order(order)
        
        # Process through matching engine
        trades = self.matching_engine.process_order(order)
        
        # Log trades to WAL and persist to database
        for trade in trades:
            self.wal.append('INSERT', 'TRADE', trade.to_dict())
            
            # Persist trade to database
            if self.db_writer:
                await self.db_writer.insert_trade(trade)
        
        # Update order status in WAL if it was modified during matching
        if order.traded_qty > 0:
            self.wal.append('UPDATE', 'ORDER', order.to_dict())
            
            # Update order in database
            if self.db_writer:
                await self.db_writer.update_order(order)
        
        # Publish trade events
        if trades:
            await self.event_publisher.publish_trades(trades)
        
        print(f"[CONSUMER] Created order {order.order_id}, executed {len(trades)} trades")
    
    async def _handle_modify_order(self, data: Dict[str, Any]):
        """
        Handle MODIFY order operation.
        
        Args:
            data: Contains order_id and updated_price_paise
        """
        order_id = data.get('order_id')
        updated_price_paise = data.get('updated_price_paise')
        
        # Get existing order
        order = self.order_book.get_order(order_id)
        if not order:
            print(f"[CONSUMER] Order {order_id} not found for modification")
            return
        
        # Remove from book
        self.order_book.remove_order(order_id)
        
        # Update price
        old_price = order.price_paise
        order.price_paise = updated_price_paise
        
        # Log to WAL
        self.wal.append('UPDATE', 'ORDER', order.to_dict())
        
        # Update in database
        if self.db_writer:
            await self.db_writer.update_order(order)
        
        # Re-process through matching engine (price change may trigger matches)
        trades = self.matching_engine.process_order(order)
        
        # Log trades to WAL and persist
        for trade in trades:
            self.wal.append('INSERT', 'TRADE', trade.to_dict())
            
            # Persist trade to database
            if self.db_writer:
                await self.db_writer.insert_trade(trade)
        
        # Publish trade events
        if trades:
            await self.event_publisher.publish_trades(trades)
        
        # Update order in WAL again if modified during matching
        if order.traded_qty > 0:
            self.wal.append('UPDATE', 'ORDER', order.to_dict())
            
            # Update in database
            if self.db_writer:
                await self.db_writer.update_order(order)
        
        print(f"[CONSUMER] Modified order {order_id} price from {old_price} to {updated_price_paise}")
    
    async def _handle_cancel_order(self, data: Dict[str, Any]):
        """
        Handle CANCEL order operation.
        
        Args:
            data: Contains order_id
        """
        order_id = data.get('order_id')
        
        # Cancel order
        order = self.order_book.cancel_order(order_id)
        
        if order:
            # Log to WAL
            self.wal.append('DELETE', 'ORDER', order.to_dict())
            
            # Update in database (status changed to CANCELLED)
            if self.db_writer:
                await self.db_writer.update_order(order)
            
            print(f"[CONSUMER] Cancelled order {order_id}")
        else:
            print(f"[CONSUMER] Order {order_id} not found for cancellation")
