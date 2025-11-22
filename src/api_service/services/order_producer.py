"""
Redis producer for pushing order requests to the order queue.

like publishing messages to a message queue in Spring Boot,
this sends order operations to Redis Streams for the OBM to consume.
"""

import json
import uuid
from datetime import datetime

from shared.constants import REDIS_ORDER_QUEUE, OperationType


class OrderProducer:
    """
    Produces order messages to Redis Streams.
    
    Think of this like a Kafka producer or RabbitMQ publisher in Spring Boot.
    """
    
    def __init__(self, redis_client):
        """
        Initialize order producer.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis_client = redis_client
    
    async def create_order(self, quantity: int, price_paise: int, side: int) -> str:
        """
        Send a CREATE order request to the queue.
        
        Args:
            quantity: Order quantity
            price_paise: Order price in paise
            side: Order side (1 for buy, -1 for sell)
            
        Returns:
            order_id: Generated order ID
        """
        # Generate order ID (like auto-generated ID in JPA)
        order_id = str(uuid.uuid4())
        
        # Create order data
        order_data = {
            "order_id": order_id,
            "side": side,
            "price_paise": price_paise,
            "original_qty": quantity,
            "remaining_qty": quantity,
            "traded_qty": 0,
            "avg_traded_price_paise": 0,
            "status": "OPEN",
            "created_timestamp": datetime.utcnow().isoformat(),
            "updated_timestamp": datetime.utcnow().isoformat()
        }
        
        # Create message payload
        message = {
            "operation": OperationType.CREATE,
            "data": json.dumps(order_data)
        }
        
        # Push to Redis Streams
        await self.redis_client.xadd(REDIS_ORDER_QUEUE, message)
        
        print(f"[PRODUCER] Sent CREATE order {order_id} to queue")
        return order_id
    
    async def modify_order(self, order_id: str, updated_price_paise: int) -> bool:
        """
        Send a MODIFY order request to the queue.
        
        Args:
            order_id: ID of order to modify
            updated_price_paise: New price in paise
            
        Returns:
            True if message sent successfully
        """
        # Create modification data
        modify_data = {
            "order_id": order_id,
            "updated_price_paise": updated_price_paise
        }
        
        # Create message payload
        message = {
            "operation": OperationType.MODIFY,
            "data": json.dumps(modify_data)
        }
        
        # Push to Redis Streams
        await self.redis_client.xadd(REDIS_ORDER_QUEUE, message)
        
        print(f"[PRODUCER] Sent MODIFY order {order_id} to queue")
        return True
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Send a CANCEL order request to the queue.
        
        Args:
            order_id: ID of order to cancel
            
        Returns:
            True if message sent successfully
        """
        # Create cancellation data
        cancel_data = {
            "order_id": order_id
        }
        
        # Create message payload
        message = {
            "operation": OperationType.CANCEL,
            "data": json.dumps(cancel_data)
        }
        
        # Push to Redis Streams
        await self.redis_client.xadd(REDIS_ORDER_QUEUE, message)
        
        print(f"[PRODUCER] Sent CANCEL order {order_id} to queue")
        return True
