"""
Redis Pub/Sub event subscriber.

Subscribes to Redis channels for trade events and order book snapshots,
then forwards them to WebSocket clients.

"""

import asyncio
import json

from ..websockets.manager import ConnectionManager
from shared.constants import REDIS_TRADE_EVENTS, REDIS_SNAPSHOT_EVENTS


class EventSubscriber:
    """
    Subscribes to Redis Pub/Sub channels and forwards events to WebSocket clients.
    
    like a message consumer in Spring Boot that processes events and pushes them to further processing (websocket in our case).
    """
    
    def __init__(self, redis_client, connection_manager: ConnectionManager):
        """
        Initialize event subscriber.
        
        Args:
            redis_client: Redis client instance
            connection_manager: WebSocket connection manager
        """
        self.redis_client = redis_client
        self.connection_manager = connection_manager
        self.pubsub = None
        self.running = False
    
    async def start(self):
        """Start subscribing to Redis Pub/Sub channels"""
        self.running = True
        
        # Create pubsub instance
        self.pubsub = self.redis_client.pubsub()
        
        # Subscribe to channels
        await self.pubsub.subscribe(REDIS_TRADE_EVENTS, REDIS_SNAPSHOT_EVENTS)
        
        print(f"[SUBSCRIBER] Subscribed to '{REDIS_TRADE_EVENTS}' and '{REDIS_SNAPSHOT_EVENTS}'")
        
        # Start listening loop
        await self._listen_loop()
    
    async def stop(self):
        """Stop subscribing"""
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe(REDIS_TRADE_EVENTS, REDIS_SNAPSHOT_EVENTS)
            await self.pubsub.close()
        print("[SUBSCRIBER] Stopped")
    
    async def _listen_loop(self):
        """
        Main listening loop for Redis Pub/Sub messages.
        
        Similar to the consume loop in a Kafka listener.
        """
        while self.running:
            try:
                # Get message from pubsub (non-blocking)
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                
                if message and message['type'] == 'message':
                    channel = message['channel']
                    data = message['data']
                    
                    # Parse JSON data
                    try:
                        event_data = json.loads(data)
                        
                        # Route to appropriate handler
                        if channel == REDIS_TRADE_EVENTS:
                            await self._handle_trade_event(event_data)
                        elif channel == REDIS_SNAPSHOT_EVENTS:
                            await self._handle_snapshot_event(event_data)
                    
                    except json.JSONDecodeError as e:
                        print(f"[SUBSCRIBER] Error parsing JSON: {e}")
                
                # Small sleep to avoid tight loop
                await asyncio.sleep(0.01)
                
            except Exception as e:
                print(f"[SUBSCRIBER] Error in listen loop: {e}")
                await asyncio.sleep(1)
    
    async def _handle_trade_event(self, trade_data: dict):
        """
        Handle a trade event and broadcast to WebSocket clients.
        
        Args:
            trade_data: Trade information
        """
        # Forward to WebSocket clients
        await self.connection_manager.broadcast_trade(trade_data)
        
        print(f"[SUBSCRIBER] Broadcasted trade event")
    
    async def _handle_snapshot_event(self, snapshot_data: dict):
        """
        Handle an order book snapshot and broadcast to WebSocket clients.
        
        Args:
            snapshot_data: Order book snapshot
        """
        # Forward to WebSocket clients
        await self.connection_manager.broadcast_snapshot(snapshot_data)
