"""
Redis Pub/Sub event publisher.

Publishes trade events and order book snapshots to Redis channels
for consumption by the API service.
"""

import json
import asyncio
from typing import List
from datetime import datetime
from shared.models import TradeRecord, OrderBookSnapshot
from shared.constants import (
    REDIS_TRADE_EVENTS,
    REDIS_SNAPSHOT_EVENTS,
    SNAPSHOT_INTERVAL_SECONDS,
    SNAPSHOT_DEPTH_LEVELS
)
from ..order_book import OrderBook


class EventPublisher:
    """
    Publishes events to Redis Pub/Sub channels.
    """
    
    def __init__(self, redis_client, order_book: OrderBook):
        """
        Initialize event publisher.
        
        Args:
            redis_client: Redis client instance
            order_book: OrderBook instance
        """
        self.redis_client = redis_client
        self.order_book = order_book
        self.running = False
    
    async def publish_trades(self, trades: List[TradeRecord]):
        """
        Publish trade events to Redis.
        
        Args:
            trades: List of TradeRecord objects to publish
        """
        for trade in trades:
            try:
                # Convert trade to dict with float prices for API
                trade_data = {
                    "trade_id": trade.trade_id,
                    "timestamp": trade.timestamp,
                    "price": trade.price_paise / 100.0,  # Convert to float
                    "qty": trade.qty,
                    "bid_order_id": trade.bid_order_id,
                    "ask_order_id": trade.ask_order_id
                }
                
                # Publish to Redis channel
                await self.redis_client.publish(
                    REDIS_TRADE_EVENTS,
                    json.dumps(trade_data)
                )
                
                print(f"[PUBLISHER] Published trade {trade.trade_id} to '{REDIS_TRADE_EVENTS}'")
                
            except Exception as e:
                print(f"[PUBLISHER] Error publishing trade: {e}")
    
    async def start_snapshot_publisher(self):
        """
        Start background task to publish order book snapshots periodically.
        """
        self.running = True
        print(f"[PUBLISHER] Starting snapshot publisher (interval: {SNAPSHOT_INTERVAL_SECONDS}s)")
        
        while self.running:
            try:
                await self._publish_snapshot()
                await asyncio.sleep(SNAPSHOT_INTERVAL_SECONDS)
            except Exception as e:
                print(f"[PUBLISHER] Error in snapshot publisher: {e}")
                await asyncio.sleep(1)
    
    async def stop_snapshot_publisher(self):
        """Stop the snapshot publisher"""
        self.running = False
        print("[PUBLISHER] Stopped snapshot publisher")
    
    async def _publish_snapshot(self):
        """Publish order book snapshot to Redis"""
        try:
            # Get snapshot from order book
            bids, asks = self.order_book.get_snapshot(depth=SNAPSHOT_DEPTH_LEVELS)
            
            # Create snapshot object
            snapshot = OrderBookSnapshot(
                timestamp=datetime.utcnow().isoformat(),
                bids=bids,
                asks=asks
            )
            
            # Publish to Redis channel
            await self.redis_client.publish(
                REDIS_SNAPSHOT_EVENTS,
                json.dumps(snapshot.to_dict())
            )
            
            # Log only if there's meaningful data
            if bids or asks:
                print(f"[PUBLISHER] Published snapshot: {len(bids)} bid levels, {len(asks)} ask levels")
            
        except Exception as e:
            print(f"[PUBLISHER] Error publishing snapshot: {e}")
